-------------------------------------------------------------------------------
-- Title      : jtag2wb - simple bridge providing control of Wishbone bus
--              via JTAG interface. You may use it e.g. to control WB
--              from Vivado Tcl console.
-- Project    : 
-------------------------------------------------------------------------------
-- File       : jtag2wb.vhd
-- Author     : Wojciech M. Zabolotny
-- License    : PUBLIC DOMAIN or Creative Commons CC0
-- Company    : 
-- Created    : 2018-12-20
-- Last update: 2019-02-20
-- Platform   : 
-- Standard   : VHDL'93
-------------------------------------------------------------------------------
-- Description:
--
--
--   That code is significantly based on my JTAG bus controller
--   published in https://groups.google.com/d/msg/alt.sources/Rh5yEuF2YGE/p6UB0RdRS-AJ
--   thread on alt.sources Usenet group.
--
--  The two MSB bits encode the operation.
--  1,0 - Sending address for READ operation (immediately triggers READ on WB)
--  1,1 - Sending address for WRITE operation (next DATA transfer triggers the
--        WRITE operation)
--  0,1 - Sending data for WRITE operation
--  0,0 - Reading status and data after READ operation, reading status after
--        WRITE operation
--
--  The WB controller operates in the WB clock domain.
--  Disappearance of the JTAG clock should not block its operation
--  and the whole WB bus (that maybe also controlled by other hosts!).
--  Therefore, implementation of the whole WB controller with JTAG clock
--  and using my WB-CDC may be not the best idea!
--  We know, that there will be at least two jt_TCK clock pulses before
--  the capture (see Ug835, decription of scan_dr_hw_jtag).
--  IDLE->DRSELECT->DRCAPTURE
--  Therefore we may use CDC requiring two jt_TCK pulses.
--  It is done with two pairs of signals: s_start:s_start_sync and
--    s_done_sync:s_done_async
--  The "ping-pong" approach is used so the new command is triggered when
--  s_start /= s_done_sync. The command is completed (successfully or not)
--  when s_start = s_done.
--  Please note, that you need to specify the appropriate timing constraints
--  for signals passed between JTAG and WB clock domains:
--  s_din, wb_status, s_address, s_data, s_mode.
--  You may also need to increase the number of synchronization stages.
--
--  The address remains unchanged after the operation. That makes implementation
--  of RMW operations easy. You may do READ (which sets the address),
--  then calculate the new value and issue WRITE (address was already set).

-------------------------------------------------------------------------------
-- Copyright (c) 2018 Wojciech M. Zabolotny (wzab<at>ise.pw.edu.pl or
--  wzab01<at>gmail.com )
-------------------------------------------------------------------------------
-- Revisions  :
-- Date        Version  Author  Description
-- 2018-12-20  1.0      wzab      Created
-------------------------------------------------------------------------------
--
--  This program is PUBLIC DOMAIN or Creative Commons CC0 code
--  You can do with it whatever you want. However, NO WARRANTY of ANY KIND
--  is provided
--
-- 

library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;
use ieee.std_logic_unsigned.all;
library work;
use work.wishbone_pkg.all;

entity jtag2wb is
  generic (
    addr_width : integer := 32;
    data_width : integer := 32);
  port (
    -- Wishbone bus connection
    master_clk_i   : in  std_logic;
    master_rst_n_i : in  std_logic;
    master_i       : in  t_wishbone_master_in;
    master_o       : out t_wishbone_master_out
    );
end jtag2wb;

architecture syn of jtag2wb is

  component BSCANE2
    generic (
      JTAG_CHAIN : integer);
    port (
      CAPTURE : out std_ulogic;
      DRCK    : out std_ulogic;
      RESET   : out std_ulogic;
      RUNTEST : out std_ulogic;
      SEL     : out std_ulogic;
      SHIFT   : out std_ulogic;
      TCK     : out std_ulogic;
      TDI     : out std_ulogic;
      TMS     : out std_ulogic;
      UPDATE  : out std_ulogic;
      TDO     : in  std_ulogic);
  end component;
  attribute ASYNC_REG : string;
  signal jt_shift, jt_update, jt_tdi, jt_tdo, jt_tck, jt_tms, jt_drck,
    jt_capture, jt_sel, jt_reset : std_ulogic;  -- := '0';


  signal s_done_sync, s_done_async : std_logic := '0';
  attribute ASYNC_REG of s_done_sync : signal is "TRUE";

  signal s_start, s_start_sync : std_logic := '0';
  attribute ASYNC_REG of s_start_sync : signal is "TRUE";

  signal s_address : std_logic_vector(addr_width-1 downto 0);
  signal s_din : std_logic_vector(data_width-1 downto 0);
  signal s_data : std_logic_vector(data_width-1 downto 0);
  
  function maximum(L, R : integer) return integer is
  begin
    if L > R then
      return L;
    else
      return R;
    end if;
  end;

  type T_MODE is (SM_READ,SM_WRITE);
  signal s_mode  : T_MODE := SM_READ;
  
  type TWB_STATE is (SWB_IDLE, SWB_WAIT_ACK);
  signal wb_state : TWB_STATE := SWB_IDLE;

  signal wb_status : std_logic := '0';
  
  constant DR_SHIFT_LEN : integer                                   := maximum(addr_width+2, data_width+2);
  -- Register storing the access address and mode (read/write)
  signal dr_shift       : std_logic_vector(DR_SHIFT_LEN-1 downto 0) := (others => '0');

begin


  BSCANE2_1 : BSCANE2
    generic map (
      JTAG_CHAIN => 1)
    port map (
      CAPTURE => jt_CAPTURE,
      DRCK    => jt_DRCK,
      RESET   => jt_RESET,
      SEL     => jt_SEL,
      SHIFT   => jt_SHIFT,
      TCK     => jt_TCK,
      TDI     => jt_TDI,
      TMS     => jt_TMS,
      UPDATE  => jt_UPDATE,
      TDO     => jt_TDO);

  -- Generate the read and write strobes
  --out_fifo_rd <= '1' when jt_capture = '1' and jt_sel = '1' and out_fifo_empty='0' else '0';
  -- Generate the write strobe for the external bus - when write_cmd, and this
  -- is the data word
  --in_fifo_wr <= '1' when jt_update = '1' and jt_sel = '1' and
  --              in_fifo_full = '0' and dr_shift(DR_SHIFT_LEN-1) = '1' else '0';

  -- Load and shift data to dr_addr_and_mode register
  -- The first process handles the JTAG access. Therefore we can't put here
  -- any waitstates.
  pjtag1 : process (jt_tck, jt_reset)
    variable oper : std_logic_vector(1 downto 0);
  begin  -- process
    if jt_reset = '1' then
      dr_shift    <= (others => '0');
      s_done_sync <= '0';
      s_start <= '0';
    elsif jt_tck'event and jt_tck = '1' then  -- falling clock edge - state
      -- Synchronization of the s_done_sync signal
      s_done_sync <= s_done_async;
      -- defaults
      oper := dr_shift(DR_SHIFT_LEN-1 downto DR_SHIFT_LEN-2);
      --
      if jt_sel = '1' then
        if jt_update = '1' then
          -- We received the JTAG command
          case oper is
            when "11" =>
              -- Write, we have to wait for data to be written
              -- So here we store the address, and set the mode to "WRITE"
              s_address <= dr_shift(addr_width-1 downto 0);
              s_mode <= SM_WRITE;
            when "10" =>
              -- Read, we have received the address to read from
              s_address <= dr_shift(addr_width-1 downto 0);
              -- Start immediately the read operation
              s_start <= not s_start;
              s_mode <= SM_READ;
            when "01" =>
              -- Data for "WRITE"
              s_mode <= SM_WRITE;       -- Added for RMW!
              s_data <= dr_shift(data_width-1 downto 0);
              s_start <= not s_start;
            when "00" =>
              -- Read the status and received data - no action needed
              null ;                        
            when others => null;
          end case;
        end if;
        if jt_capture = '1' then
          if s_start = s_done_sync then
            -- Read the data
            dr_shift <= (others => '0');            
            dr_shift(DR_SHIFT_LEN-1) <= '1';
            dr_shift(DR_SHIFT_LEN-2) <= wb_status;
            -- Read the dout from the WB controller
            dr_shift(data_width-1 downto 0) <= s_din;
          else
            -- Operation in progress
            dr_shift <= (others => '0');
          end if;
        end if;
        if jt_shift = '1' then
          -- Shift the register
          dr_shift(DR_SHIFT_LEN-1) <= jt_tdi;
          for i in 0 to DR_SHIFT_LEN-2 loop
            dr_shift(i) <= dr_shift(i+1);
          end loop;  -- i
        end if;
      end if;
    end if;
  end process pjtag1;
  jt_TDO <= dr_shift(0);

  -- Here is the implementation of the WB controller with CDC
  wpm: process (master_clk_i) is
  begin  -- process wpm
    if master_clk_i'event and master_clk_i = '1' then  -- rising clock edge
      if master_rst_n_i = '0' then      -- synchronous reset (active low)
        master_o.cyc <= '0';
        master_o.stb <= '0';
        master_o.adr <= (others => '0');
        master_o.dat <= (others => '0');
        wb_state <= SWB_IDLE;
        s_done_async <= '0';
        s_start_sync <= '0';
      else
        -- Synchronize the start signal
        s_start_sync <= s_start;
        -- Main state machine
        case wb_state is
          when SWB_IDLE =>
            if s_start_sync /= s_done_async then
              -- New operation is scheduled
              -- Check if it is read or write
              master_o.adr <= s_address;
              master_o.dat <= s_data;
              master_o.stb <= '1';
              master_o.cyc <= '1';
              master_o.sel <= (others => '1');
              if s_mode = SM_WRITE then
                master_o.we <= '1';
              else
                master_o.we <= '0';
              end if;
              wb_state <= SWB_WAIT_ACK;
            end if;
          when SWB_WAIT_ACK =>
            if master_i.ack = '1' then
              s_din <= master_i.dat;
              wb_status <= '1';
              s_done_async <= s_start_sync;
              master_o.stb <= '0';
              master_o.cyc <= '0';
              wb_state <= SWB_IDLE;
            end if;
            if master_i.err = '1' then
              s_din <= master_i.dat;
              wb_status <= '0';
              s_done_async <= s_start_sync;
              master_o.stb <= '0';
              master_o.cyc <= '0';
              wb_state <= SWB_IDLE;
            end if;
          when others => null;
        end case;
          
      end if;
    end if;
  end process wpm;
  

end syn;
