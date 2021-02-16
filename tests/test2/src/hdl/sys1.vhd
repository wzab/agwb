library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;
library general_cores;
use general_cores.wishbone_pkg.all;
library agwb;
use agwb.agwb_pkg;
use agwb.sys1_pkg.all;
library work;

entity sys1 is
  generic (
    nvar : integer := 0
    );
  port (
    rst_n_i   : in  std_logic;
    clk_sys_i : in  std_logic;
    wb_s_in   : in  t_wishbone_slave_in;
    wb_s_out  : out t_wishbone_slave_out
    );

end entity sys1;

architecture rtl of sys1 is

  signal slave_i      : t_wishbone_slave_in;
  signal slave_o      : t_wishbone_slave_out;
  signal CTRL_o       : t_CTRL;
  signal CTRL_o_stb   : std_logic;
  signal STATUS_i     : ut_STATUS_array(v_STATUS_size(nvar)-1 downto 0);
  signal STATUS_i_ack : std_logic_vector(v_STATUS_size(nvar)-1 downto 0);
  signal ENABLEs_o    : ut_ENABLEs_array(v_ENABLES_size(nvar)-1 downto 0);

begin  -- architecture rtl

  SYS1_wb_1 : entity agwb.SYS1
    generic map (
      g_STATUS_size  => v_STATUS_size(nvar),
      g_ENABLEs_size => v_ENABLES_size(nvar))
    port map (
      slave_i      => wb_s_in,
      slave_o      => wb_s_out,
      CTRL_o       => CTRL_o,
      CTRL_o_stb   => CTRL_o_stb,
      STATUS_i     => STATUS_i,
      STATUS_i_ack => STATUS_i_ack,
      ENABLEs_o    => ENABLEs_o,
      rst_n_i      => rst_n_i,
      clk_sys_i    => clk_sys_i);

end architecture rtl;
