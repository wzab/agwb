library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;
library general_cores;
use general_cores.wishbone_pkg.all;
library agwb;
use agwb.sys1_pkg.all;
library work;
  
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
  signal CTRL_o_stb    : std_logic;
  signal STATUS_i  : t_STATUS;
  signal STATUS_i_ack  : std_logic;
  signal ENABLEs_o : t_ENABLEs_array(0 to c_ENABLEs_size-1);
  
begin  -- architecture rtl

  SYS1_1: entity agwb.SYS1
    port map (
      slave_i   => wb_s_in,
      slave_o   => wb_s_out,
      CTRL_o    => CTRL_o,
      CTRL_o_stb    => CTRL_o_stb,
      STATUS_i  => STATUS_i,
      STATUS_i_ack  => STATUS_i_ack,
      ENABLEs_o => ENABLEs_o,
      rst_n_i   => rst_n_i,
      clk_sys_i => clk_sys_i);
  
end architecture rtl;
