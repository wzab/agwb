library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;
library work;
use work.wishbone_pkg.all;

entity exttest is
  generic (
    instance_number : integer := 0;
    addr_size       : integer := 8);

  port (
    rst_n_i   : in  std_logic;
    clk_sys_i : in  std_logic;
    wb_s_in   : in  t_wishbone_slave_in;
    wb_s_out  : out t_wishbone_slave_out
    );

end entity exttest;

architecture rtl of exttest is

  signal ack : std_logic := '0';

begin  -- architecture rtl

  process(clk_sys_i)
    variable int_addr : unsigned(addr_size-1 downto 0);
  begin
    if rising_edge(clk_sys_i) then
      if rst_n_i = '0' then
        report "EXTERN " & integer'image(instance_number) & " is reset" severity note;
      else
        -- Normal operation
        wb_s_out.rty <= '0';
        ack          <= '0';
        wb_s_out.err <= '0';
        if (wb_s_in.cyc = '1') and (wb_s_in.stb = '1') then
          int_addr := unsigned(wb_s_in.adr(addr_size-1 downto 0));
          if wb_s_in.we = '1' then
            if ack = '0' then
              report "EXTERN " & integer'image(instance_number) &
                " writing " & integer'image(to_integer(unsigned(wb_s_in.dat))) &
                " to address " & integer'image(to_integer(int_addr)) severity note;
            end if;
          else
            if ack = '0' then
              report "EXTERN " & integer'image(instance_number) &
                " reading from address " & integer'image(to_integer(int_addr)) severity note;
              wb_s_out.dat <= x"56781234";
            end if;
          end if;
          ack <= '1';
        end if;
      end if;
    end if;
  end process;

  wb_s_out.ack <= ack;

end architecture rtl;
