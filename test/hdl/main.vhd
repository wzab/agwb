library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;
library work;
use work.wishbone_pkg.all;
use work.MAIN_wb_pkg.all;
  
entity main is
  
  port (
    rst_n_i : in std_logic;
    clk_sys_i : in std_logic;
    wb_s_in  : in  t_wishbone_slave_in;
    wb_s_out : out t_wishbone_slave_out
    );

end entity main;

architecture rtl of main is
  signal LINKS_wb_s_o : t_wishbone_slave_out_array(0 to 4);
  signal LINKS_wb_s_i : t_wishbone_slave_in_array(0 to 4);
  signal CTRL_o       : t_CTRL;
begin  -- architecture rtl

  MAIN_wb_1: entity work.MAIN_wb
    port map (
      slave_i      => wb_s_in,
      slave_o      => wb_s_out,
      LINKS_wb_s_o => LINKS_wb_s_o,
      LINKS_wb_s_i => LINKS_wb_s_i,
      CTRL_o       => CTRL_o,
      rst_n_i      => rst_n_i,
      clk_sys_i    => clk_sys_i);

  gl1: for i in 0 to 4 generate

    sys1_1: entity work.sys1
      port map (
        rst_n_i   => rst_n_i,
        clk_sys_i => clk_sys_i,
        wb_s_in   => LINKS_wb_s_i(i),
        wb_s_out  => LINKS_wb_s_o(i));
    
  end generate gl1;

  
end architecture rtl;
