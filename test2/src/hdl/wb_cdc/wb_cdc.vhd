-------------------------------------------------------------------------------
-- Title      : Wishbone CDC for classic single cycles
-- Project    : 
-------------------------------------------------------------------------------
-- File       : wb_cdc.vhd
-- Author     : Wojciech Zabolotny  <wzab01@gmail.com> or <wzab@ise.pw.edu.pl>
-- Company    : 
-- Created    : 2018-03-11
-- Last update: 2019-02-20
-- Platform   :
-- Standard   : VHDL'93/02
-- License    : PUBLIC DOMAIN or Creative Commons CC0
-------------------------------------------------------------------------------
-- Description:
-- This is a simple CDC block, transmitting the Wishbone accesses from
-- the "SLAVE" clock domain to the "MASTER" clock domain.
-- Please note, that the block requires timing constraints, limiting
-- 1) the bus skew between the address, data and WE lines for transmission
--    from SLAVE to MASTER side.
-- 2) the bus skew between the data, ACK, ERR, and RTY lines for
--    transmission from MASTER to SLAVE.
-------------------------------------------------------------------------------
-- Copyright (c) 2018 
-------------------------------------------------------------------------------
-- Revisions  :
-- Date        Version  Author  Description
-- 2018-03-11  1.0      xl      Created
-------------------------------------------------------------------------------
library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;
library general_cores;
use general_cores.wishbone_pkg.all;
library work;

entity wb_cdc is

  generic (
    width : integer := 32);

  port (
    -- Part connecting to the master (as a slave), working in the first clock domain
    slave_clk_i    : in  std_logic;
    slave_rst_n_i  : in  std_logic;
    slave_i        : in  t_wishbone_slave_in;
    slave_o        : out t_wishbone_slave_out;
    -- Part connecting to slaves (as the master) working in the second clock domain
    master_clk_i   : in  std_logic;
    master_rst_n_i : in  std_logic;
    master_i       : in  t_wishbone_master_in;
    master_o       : out t_wishbone_master_out
    );

end entity wb_cdc;


architecture rtl of wb_cdc is

  attribute ASYNC_REG : string;

  signal req, req_m0, req_m1, req_m       : std_logic := '0';
  attribute ASYNC_REG of req_m0, req_m1   : signal is "TRUE";
  signal resp, resp_s0, resp_s1, resp_m   : std_logic := '0';
  attribute ASYNC_REG of resp_s0, resp_s1 : signal is "TRUE";

  signal rst_sl_0, rst_sl_p, rst_ms_0, rst_ms_p : std_logic                          := '1';
  signal dat_m                                  : std_logic_vector(width-1 downto 0) := (others => '0');
  signal ack_m, rty_m, err_m                    : std_logic                          := '0';

  type t_ms_state is (ST_IDLE, ST_CYCLE, ST_TERM);
  signal ms_state : t_ms_state := ST_IDLE;

begin  -- architecture rtl

  -- Synchronization of reset for slave side
  --r1 : process (slave_clk_i, slave_rst_n_i) is
  --begin  -- process r1
  --  if slave_rst_n_i = '0' then         -- asynchronous reset (active high)
  --    rst_sl_0 <= '1';
  --    rst_sl_p <= '1';
  --  elsif slave_clk_i'event and slave_clk_i = '1' then  -- rising clock edge
  --    rst_sl_p <= rst_sl_0;
  --    rst_sl_0 <= '0';
  --  end if;
  --end process r1;

  rst_ms_p <= not master_rst_n_i;
  
  -- Synchronization of reset for master side
  -- r2 : process (master_clk_i, master_rst_n_i) is
  -- begin  -- process r1
  --   if master_rst_n_i = '0' then        -- asynchronous reset (active high)
  --     rst_ms_0 <= '1';
  --     rst_ms_p <= '1';
  --   elsif master_clk_i'event and master_clk_i = '1' then  -- rising clock edge
  --     rst_ms_p <= rst_ms_0;
  --     rst_ms_p <= '0';
  --   end if;
  -- end process r2;

  rst_sl_p <= not slave_rst_n_i;
  
  -- How does it work
  -- If on the slave side we find that cyc&stb changed its state from 0 to 1,
  -- We trigger access, by toggling the request line.

  sync_s1 : process (slave_clk_i) is
  begin  -- process sync_s1
    if slave_clk_i'event and slave_clk_i = '1' then  -- rising clock edge
      if rst_sl_p = '1' then            -- synchronous reset (active high)
        req         <= '0';
        resp        <= '0';
        resp_s1     <= '0';
        resp_s0     <= '0';
        slave_o.ack <= '0';
        ms_state    <= ST_IDLE;
      else
        -- defaults
        slave_o.ack <= '0';
        slave_o.err <= '0';
        slave_o.rty <= '0';
        case ms_state is
          when ST_IDLE =>
            if (slave_i.cyc = '1') and (slave_i.stb = '1') then
              ms_state <= ST_CYCLE;
              req      <= not req;
            end if;
          when ST_CYCLE =>
            if (slave_i.cyc = '1') and (slave_i.stb = '1') and (resp = req) then
              slave_o.dat <= dat_m;
              slave_o.ack <= ack_m;
              slave_o.err <= err_m;
              slave_o.rty <= rty_m;
              ms_state    <= ST_TERM;
            end if;
          when ST_TERM =>
            ms_state <= ST_IDLE;
        end case;
        -- Propagation of signals from master
        resp    <= resp_s1;
        resp_s1 <= resp_s0;
        resp_s0 <= resp_m;
      end if;
    end if;
  end process sync_s1;


  -- purpose: synchronization at master side
  -- type   : sequential
  -- inputs : master_clk_i, master_rst_n_i
  -- outputs: 
  sync_m1 : process (master_clk_i) is
  begin  -- process sync_m1
    if master_clk_i'event and master_clk_i = '1' then  -- rising clock edge
      if rst_ms_p = '1' then            -- synchronous reset (active high)
        req_m0 <= '0';
        req_m1 <= '0';
        req_m  <= '0';
        dat_m  <= (others => '0');
        ack_m  <= '0';
        rty_m  <= '0';
        err_m  <= '0';
      else
        req_m0 <= req;
        req_m1 <= req_m0;
        req_m  <= req_m1;
        if req_m /= resp_m then
          -- Copy address, data and WE
          master_o.adr <= slave_i.adr;
          master_o.dat <= slave_i.dat;
          master_o.we  <= slave_i.we;
          -- Start the access
          master_o.cyc <= '1';
          master_o.stb <= '1';
          -- Clear the old statuses
          err_m        <= '0';
          ack_m        <= '0';
          rty_m        <= '0';
        end if;
        -- Handle ACK
        if (master_i.ack = '1') or (master_i.err = '1') or (master_i.rty = '1') then
          master_o.cyc <= '0';
          master_o.stb <= '0';
          dat_m        <= master_i.dat;
          err_m        <= master_i.err;
          ack_m        <= master_i.ack;
          rty_m        <= master_i.rty;
          resp_m       <= req_m;
        end if;
      end if;
    end if;
  end process sync_m1;

end architecture rtl;
