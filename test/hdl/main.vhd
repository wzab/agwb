library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;
library general_cores;
use general_cores.wishbone_pkg.all;
library work;
use work.agwb_MAIN_const_pkg.all;
use work.agwb_MAIN_wb_pkg.all;

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
  signal LINKS_wb_m_o  : t_wishbone_master_out_array(0 to NSEL_MAX-1);
  signal LINKS_wb_m_i  : t_wishbone_master_in_array(0 to NSEL_MAX-1);
  signal EXTHUGE_wb_m_o : t_wishbone_master_out;
  signal EXTHUGE_wb_m_i : t_wishbone_master_in;
  signal EXTERN_wb_m_o : t_wishbone_master_out_array(0 to (NEXTERNS-1));
  signal EXTERN_wb_m_i : t_wishbone_master_in_array(0 to (NEXTERNS-1));
  signal CDC_wb_m_o    : t_wishbone_master_out_array(0 to (NEXTERNS-1));
  signal CDC_wb_m_i    : t_wishbone_master_in_array(0 to (NEXTERNS-1));
  signal CTRL_o        : t_CTRL;
begin  -- architecture rtl

  MAIN_wb_1 : entity work.agwb_MAIN_wb
    port map (
      slave_i       => wb_s_in,
      slave_o       => wb_s_out,
      LINKS_wb_m_o  => LINKS_wb_m_o,
      LINKS_wb_m_i  => LINKS_wb_m_i,
      EXTHUGE_wb_m_o => EXTHUGE_wb_m_o,
      EXTHUGE_wb_m_i => EXTHUGE_wb_m_i,
      EXTERN_wb_m_o => CDC_wb_m_o,
      EXTERN_wb_m_i => CDC_wb_m_i,
      CTRL_o        => CTRL_o,
      rst_n_i       => rst_n_i,
      clk_sys_i     => clk_sys_i);

gl0: for i in 0 to NEXTERNS-1 generate
  wb_cdc_1 : entity work.wb_cdc
    generic map (
      width => 32)
    port map (
      slave_clk_i    => clk_sys_i,
      slave_rst_n_i  => rst_n_i,
      slave_i        => CDC_wb_m_o(i),
      slave_o        => CDC_wb_m_i(i),
      master_clk_i   => clk_io_i,
      master_rst_n_i => rst_n_i,
      master_i       => EXTERN_wb_m_i(i),
      master_o       => EXTERN_wb_m_o(i));

  ext_1 : entity work.exttest
    generic map (
      instance_number => i,
      addr_size       => 10
      )
    port map (
      rst_n_i   => rst_n_i,
      clk_sys_i => clk_sys_i,
      wb_s_in   => EXTERN_wb_m_o(i),
      wb_s_out  => EXTERN_wb_m_i(i));

end generate gl0;

  htst_1 : entity work.htest
    generic map (
      instance_number => 0,
      addr_size       => 16
      )
    port map (
      rst_n_i   => rst_n_i,
      clk_sys_i => clk_sys_i,
      wb_s_in   => EXTHUGE_wb_m_o,
      wb_s_out  => EXTHUGE_wb_m_i);
     
  gl1 : for i in 0 to NSEL_MAX-1 generate

    sys1_1 : entity work.sys1
      port map (
        rst_n_i   => rst_n_i,
        clk_sys_i => clk_sys_i,
        wb_s_in   => LINKS_wb_m_o(i),
        wb_s_out  => LINKS_wb_m_i(i));

  end generate gl1;

end architecture rtl;
