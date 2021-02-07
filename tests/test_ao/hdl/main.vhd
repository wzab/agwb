library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;
library general_cores;
use general_cores.wishbone_pkg.all;
library agwb;
use agwb.MAIN_const_pkg.all;
use agwb.MAIN_pkg.all;
library work;

entity main is

  port (
    rst_n_i   : in  std_logic;
    clk_sys_i : in  std_logic;
    clk_io_i  : in  std_logic;
    wb_s_in   : in  t_wishbone_slave_in;
    wb_s_out  : out t_wishbone_slave_out
    );

end entity main;

architecture rtl of main is

  -- Constant used to check a possibility to reduce the length of inplemented vector
  -- Set to 4 to check if you can reduce the length.
  -- Set to 13 to check if the assertion checking works correctly.
  constant real_TEST_IN_size : integer := 4 ;

  -- That constant checks if we can block a single register set to 0 (to get an error) or to 1
  constant real_CTRL_size : integer := 1;

  signal LINKS_wb_m_o	: t_wishbone_master_out_array(C_NSEL_MAX-1 downto 0);
  signal LINKS_wb_m_i	: t_wishbone_master_in_array(C_NSEL_MAX-1 downto 0);
  signal EXTHUGE_wb_m_o : t_wishbone_master_out;
  signal EXTHUGE_wb_m_i : t_wishbone_master_in;
  signal EXTERN_wb_m_o	: t_wishbone_master_out_array((C_NEXTERNS-1) downto 0);
  signal EXTERN_wb_m_i	: t_wishbone_master_in_array((C_NEXTERNS-1) downto 0);
  signal CDC_wb_m_o	: t_wishbone_master_out_array((C_NEXTERNS-1) downto 0);
  signal CDC_wb_m_i	: t_wishbone_master_in_array((C_NEXTERNS-1) downto 0);
  signal CTRL_o		: t_CTRL;
  signal TEST_IN_i	: ut_TEST_IN_array(real_TEST_IN_size - 1 downto 0)  := (others => (others => '0'));
  signal TEST_OUT_o	: ut_TEST_OUT_array(c_TEST_OUT_size - 1 downto 0) := (others => (others => '0'));
begin  -- architecture rtl

  MAIN_1 : entity agwb.MAIN
    generic map (
      g_CTRL_size => real_CTRL_size,
      g_TEST_IN_SIZE => real_TEST_IN_size)
    port map (
      slave_i	     => wb_s_in,
      slave_o	     => wb_s_out,
      LINKS_wb_m_o   => LINKS_wb_m_o,
      LINKS_wb_m_i   => LINKS_wb_m_i,
      EXTHUGE_wb_m_o => EXTHUGE_wb_m_o,
      EXTHUGE_wb_m_i => EXTHUGE_wb_m_i,
      EXTERN_wb_m_o  => CDC_wb_m_o,
      EXTERN_wb_m_i  => CDC_wb_m_i,
      CTRL_o	     => CTRL_o,
      TEST_IN_i	     => TEST_IN_i,
      TEST_OUT_o     => TEST_OUT_o,
      rst_n_i	     => rst_n_i,
      clk_sys_i	     => clk_sys_i);

  TEST_IN_i(0) <= x"1234";
  TEST_IN_i(1) <= x"7654";
  
  gl0 : for i in 0 to C_NEXTERNS-1 generate
    wb_cdc_1 : entity work.wb_cdc
      generic map (
	width => 32)
      port map (
	slave_clk_i    => clk_sys_i,
	slave_rst_n_i  => rst_n_i,
	slave_i	       => CDC_wb_m_o(i),
	slave_o	       => CDC_wb_m_i(i),
	master_clk_i   => clk_io_i,
	master_rst_n_i => rst_n_i,
	master_i       => EXTERN_wb_m_i(i),
	master_o       => EXTERN_wb_m_o(i));

    ext_1 : entity work.exttest
      generic map (
	instance_number => i,
	addr_size	=> 10
	)
      port map (
	rst_n_i	  => rst_n_i,
	clk_sys_i => clk_sys_i,
	wb_s_in	  => EXTERN_wb_m_o(i),
	wb_s_out  => EXTERN_wb_m_i(i));

  end generate gl0;

  htst_1 : entity work.htest
    generic map (
      instance_number => 0,
      addr_size	      => 16
      )
    port map (
      rst_n_i	=> rst_n_i,
      clk_sys_i => clk_sys_i,
      wb_s_in	=> EXTHUGE_wb_m_o,
      wb_s_out	=> EXTHUGE_wb_m_i);

  gl1 : for i in 0 to C_NSEL_MAX-1 generate

    sys1_1 : entity work.sys1
      port map (
	rst_n_i	  => rst_n_i,
	clk_sys_i => clk_sys_i,
	wb_s_in	  => LINKS_wb_m_o(i),
	wb_s_out  => LINKS_wb_m_i(i));

  end generate gl1;

end architecture rtl;
