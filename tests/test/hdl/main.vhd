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
  constant nvar : integer := 0;

  signal LINKS_wb_m_o	: t_wishbone_master_out_array(0 to v_LINKS_size(nvar)-1);
  signal LINKS_wb_m_i	: t_wishbone_master_in_array(0 to v_LINKS_size(nvar)-1);
  signal EXTHUGE_wb_m_o : t_wishbone_master_out;
  signal EXTHUGE_wb_m_i : t_wishbone_master_in;
  signal EXTERN_wb_m_o	: t_wishbone_master_out_array(0 to (C_NEXTERNS-1));
  signal EXTERN_wb_m_i	: t_wishbone_master_in_array(0 to (C_NEXTERNS-1));
  signal CDC_wb_m_o	: t_wishbone_master_out_array(0 to (C_NEXTERNS-1));
  signal CDC_wb_m_i	: t_wishbone_master_in_array(0 to (C_NEXTERNS-1));
  signal CTRL_o		: t_CTRL;
  signal TEST_IN_i	: t_TEST_IN_array(0 to c_TEST_IN_size-1)  := (others => (others => '0'));
  signal TEST_OUT_o	: t_TEST_OUT_array(0 to c_TEST_OUT_size-1) := (others => (others => '0'));
begin  -- architecture rtl

  MAIN_1 : entity agwb.MAIN
    generic map(
      g_LINKS_size => v_LINKS_size(nvar))
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

  gl1 : for i in 0 to v_LINKS_size(nvar)-1 generate

    sys1_1 : entity work.sys1
      generic map (
        nvar => 0
        )
      port map (
	rst_n_i	  => rst_n_i,
	clk_sys_i => clk_sys_i,
	wb_s_in	  => LINKS_wb_m_o(i),
	wb_s_out  => LINKS_wb_m_i(i));

  end generate gl1;

end architecture rtl;
