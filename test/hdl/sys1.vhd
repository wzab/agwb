library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;
library work;
use work.wishbone_pkg.all;
use work.sys1_wb_pkg.all;
  
entity sys1 is
  
  port (
    rst_n_i : in std_logic;
    clk_sys_i : in std_logic;
    wb_s_in  : in  t_wishbone_slave_in;
    wb_s_out : out t_wishbone_slave_out
    );

end entity sys1;

architecture rtl of sys1 is

  signal slave_i   : t_wishbone_slave_in;
  signal slave_o   : t_wishbone_slave_out;
  signal CTRL_o    : t_CTRL;
  signal STATUS_i  : t_STATUS;
  signal ENABLEs_o : t_ENABLEs_array;
  
begin  -- architecture rtl

  SYS1_wb_1: entity work.SYS1_wb
    port map (
      slave_i   => slave_i,
      slave_o   => slave_o,
      CTRL_o    => CTRL_o,
      STATUS_i  => STATUS_i,
      ENABLEs_o => ENABLEs_o,
      rst_n_i   => rst_n_i,
      clk_sys_i => clk_sys_i);
  
end architecture rtl;
