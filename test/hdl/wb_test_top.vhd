-- Code used to implement the emulated bus
-- according to method publicly disclosed by W.M.Zabolotny in 2007 
-- Usenet alt.sources "Bus controller model for VHDL & Python cosimulation"
 
library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;
use std.textio.all;
use work.wishbone_pkg.all;
library work;

entity wb_test_top is
  
  generic (
    rdpipename : string  := "rdpipe";
    wrpipename : string  := "wrpipe"
    );

  port (
    rst_i : in std_logic;
    clk_sys_i : in std_logic
    );

end wb_test_top;

architecture simul of wb_test_top is

  constant addrwidth, datawidth : integer := 32;

  signal wb_m_out   : t_wishbone_master_out := c_DUMMY_WB_MASTER_OUT;
  signal wb_m_in  : t_wishbone_master_in := c_DUMMY_WB_MASTER_IN;

  signal rst_n_i : std_logic;
  
begin  -- simul

  rst_n_i <= not rst_i;

  sim_wb_ctrl_1: entity work.sim_wb_ctrl
  generic map (
    rdpipename => rdpipename,
    wrpipename => wrpipename)
  port map (
    wb_m_out  => wb_m_out,
    wb_m_in   => wb_m_in,
    clk_sys_i => clk_sys_i);

  main_1: entity work.main
    port map (
      rst_n_i   => rst_n_i,
      clk_sys_i => clk_sys_i,
      wb_s_in   => wb_m_out,
      wb_s_out  => wb_m_in);
  
end simul;
