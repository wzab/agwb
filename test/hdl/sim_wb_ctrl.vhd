-- Code used to implement the emulated bus
-- according to method publicly disclosed by W.M.Zabolotny in 2007 
-- Usenet alt.sources "Bus controller model for VHDL & Python cosimulation"

library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;
use std.textio.all;
use work.wishbone_pkg.all;
library work;

entity sim_wb_ctrl is

  generic (
    rdpipename : string := "rdpipe";
    wrpipename : string := "wrpipe"
    );

  port (
    wb_m_out  : out t_wishbone_master_out := c_DUMMY_WB_MASTER_OUT;
    wb_m_in   : in  t_wishbone_master_in := c_DUMMY_WB_MASTER_IN;
    clk_sys_i : in  std_logic
    );

end sim_wb_ctrl;

architecture simul of sim_wb_ctrl is

  constant addrwidth, datawidth : integer := 32;

begin  -- simul



  process

    file write_pipe          : text;
    file read_pipe           : text;
    variable code            : character;
    variable db_line         : line;
    variable rd_line         : line;
    variable wr_line         : line;
    variable sync_with_slope : boolean := false;
    variable status          : boolean := false;

    procedure read_hex_stlv (
      variable fline : inout line;
      constant nbits :       integer;
      variable res   : out   std_logic_vector) is

      variable tmp          : std_logic_vector((nbits+3) downto 0) := (others => '0');
      variable c            : character;
      variable npos, nchars : integer;
    begin  -- readhex
      nchars := (nbits+3)/4;            -- number of hex chars to read
      for i in nchars-1 downto 0 loop
        npos := i*4+3;
        read (fline, c);
        case c is
          when '0' =>
            tmp(npos downto npos-3) := "0000";
          when '1' =>
            tmp(npos downto npos-3) := "0001";
          when '2' =>
            tmp(npos downto npos-3) := "0010";
          when '3' =>
            tmp(npos downto npos-3) := "0011";
          when '4' =>
            tmp(npos downto npos-3) := "0100";
          when '5' =>
            tmp(npos downto npos-3) := "0101";
          when '6' =>
            tmp(npos downto npos-3) := "0110";
          when '7' =>
            tmp(npos downto npos-3) := "0111";
          when '8' =>
            tmp(npos downto npos-3) := "1000";
          when '9' =>
            tmp(npos downto npos-3) := "1001";
          when 'a' =>
            tmp(npos downto npos-3) := "1010";
          when 'A' =>
            tmp(npos downto npos-3) := "1010";
          when 'b' =>
            tmp(npos downto npos-3) := "1011";
          when 'B' =>
            tmp(npos downto npos-3) := "1011";
          when 'c' =>
            tmp(npos downto npos-3) := "1100";
          when 'C' =>
            tmp(npos downto npos-3) := "1100";
          when 'd' =>
            tmp(npos downto npos-3) := "1101";
          when 'D' =>
            tmp(npos downto npos-3) := "1101";
          when 'e' =>
            tmp(npos downto npos-3) := "1110";
          when 'E' =>
            tmp(npos downto npos-3) := "1110";
          when 'f' =>
            tmp(npos downto npos-3) := "1111";
          when 'F' =>
            tmp(npos downto npos-3) := "1111";
          when others =>
            assert(false)
              report "Error: wrong separator in the write command" severity error;
        end case;
      end loop;  -- i
      res := tmp((nbits-1) downto 0);
    end read_hex_stlv;

    procedure write_stlv_hex2 (
      res          : inout line;
      constant vec :       std_logic_vector) is
      variable nibble  : integer;
      constant hexdigs : string := "0123456789abcdef";
    begin  -- stlv2hex
      nibble      := 0;
      if vec'left <= vec'right then
        for i in vec'left to vec'right loop
          if vec(i) = '1' then
            nibble := nibble + 2**(i-vec'left);
          end if;
        end loop;  -- i
      else
        for i in vec'right to vec'left loop
          if vec(i) = '1' then
            nibble := nibble + 2**(i-vec'right);
          end if;
        end loop;  -- i
      end if;
      write(res, nibble);
    end write_stlv_hex2;

    procedure write_stlv_hex (
      res          : inout line;
      constant vec :       std_logic_vector) is
      variable nibble  : integer;
      variable pos     : integer;
      constant hexdigs : string := "0123456789abcdef";
    begin  -- stlv2hex
      nibble       := 1;
      if vec'right <= vec'left then
        for i in vec'left downto vec'right loop
          -- calculate the nibbles
          pos := i mod 4;
          if vec(i) = '1' then
            nibble := nibble + 2**(pos);
          end if;
          if pos = 0 then
            write(res, hexdigs(nibble));
            nibble := 1;
          end if;
        end loop;  -- i
      else
        for i in vec'right downto vec'left loop
          pos := i mod 4;
          if vec(i) = '1' then
            nibble := nibble + 2**(pos);
          end if;
          if pos = 0 then
            write(res, hexdigs(nibble));
            nibble := 1;
          end if;
        end loop;  -- i
      end if;
    end write_stlv_hex;

    procedure bus_read (
      variable address : in  std_logic_vector((addrwidth-1) downto 0);
      variable data    : out std_logic_vector((datawidth-1) downto 0);
      variable status  : out boolean
      ) is
    begin  -- ipbus_read
      if sync_with_slope = false then
        wait until rising_edge(clk_sys_i);
        sync_with_slope := true;
      end if;
      wb_m_out.adr <= address;
      wb_m_out.we  <= '0';
      wb_m_out.stb <= '1';
      wb_m_out.cyc <= '1';
      wb_m_out.sel <= (others => '0');
      lr1 : loop
        wait until rising_edge(clk_sys_i);
        if wb_m_in.ack = '1' then
          data   := wb_m_in.dat;
          status := true;
          exit lr1;
        end if;
        if wb_m_in.err = '1' then
          data   := (others => '0');
          status := false;
          exit lr1;
        end if;
      end loop;
      wb_m_out.stb <= '0';
      wb_m_out.cyc <= '0';
      lr2 : loop
        wait until rising_edge(clk_sys_i);
        if (wb_m_in.ack = '0') and
          (wb_m_in.err = '0')and
          (wb_m_in.rty = '0')
        then
          exit lr2;
        end if;
      end loop;
    end bus_read;

    procedure bus_write (
      variable address : in  std_logic_vector((addrwidth-1) downto 0);
      variable data    : in  std_logic_vector((datawidth-1) downto 0);
      variable status  : out boolean
      ) is
    begin
      --report "Started bus_write" severity note;
      if sync_with_slope = false then
        wait until rising_edge(clk_sys_i);
        sync_with_slope := true;
      end if;
      wb_m_out.adr <= address;
      wb_m_out.dat <= data;
      wb_m_out.we  <= '1';
      wb_m_out.stb <= '1';
      wb_m_out.cyc <= '1';
      wb_m_out.sel <= (others => '1');
      lw1 : loop
        wait until rising_edge(clk_sys_i);
        if wb_m_in.ack = '1' then
          status := true;
          exit lw1;
        end if;
        if wb_m_in.err = '1' then
          status := false;
          exit lw1;
        end if;
      end loop;
      wb_m_out.stb <= '0';
      wb_m_out.cyc <= '0';
      wb_m_out.we  <= '0';
      lw2 : loop
        wait until rising_edge(clk_sys_i);
        if (wb_m_in.ack = '0') and
          (wb_m_in.err = '0')and
          (wb_m_in.rty = '0')
        then
          exit lw2;
        end if;
      end loop;
    end bus_write;

    variable delay   : integer;
    variable data    : std_logic_vector(31 downto 0);
    variable address : std_logic_vector(31 downto 0);

  begin  -- process
    file_open(write_pipe, wrpipename, read_mode);
    file_open(read_pipe, rdpipename, write_mode);
    wb_m_out <= c_DUMMY_WB_MASTER_OUT;
    while not endfile(write_pipe) loop
      -- We read the command from the wrpipe
      readline (write_pipe, rd_line);
      -- Analyze the line (Waddress,data)
      read (rd_line, code);
      case code is
        when 'W' =>
          read_hex_stlv(rd_line, addrwidth, address);
          read (rd_line, code);
          if code /= ',' then
            assert(false)
              report "Error: wrong separator in the write command" severity error;
          end if;
          read_hex_stlv(rd_line, datawidth, data);
          bus_write(address, data, status);
          if status then
            write(wr_line, string'("ACK"));
          else
            write(wr_line, string'("ERR"));
          end if;
          writeline(read_pipe, wr_line);
        -- If you are using VHDL-2008, you may uncomment
        -- the flush command below, and run GHDL without
        -- "--unbuffered" option
        --flush(read_pipe);
        when 'R' =>
          read_hex_stlv(rd_line, addrwidth, address);
          bus_read(address, data, status);
          if status then
            write_stlv_hex(wr_line, data);
          else
            write(wr_line, string'("ERR"));
          end if;
          writeline(read_pipe, wr_line);
        -- If you are using VHDL-2008, you may uncomment
        -- the flush command below, and run GHDL without
        -- "--unbuffered" option
        --flush(read_pipe);
        when 'T' =>
          read_hex_stlv(rd_line, 32, data);
          delay           := to_integer(unsigned(data));
          wait for delay * 1 ns;
          sync_with_slope := false;
        when others =>
          assert(false)
            report "Error: wrong character at the begining of the line" severity error;
      end case;
    end loop;
    wait;
  end process;


end simul;
