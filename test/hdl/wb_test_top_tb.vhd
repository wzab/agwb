-------------------------------------------------------------------------------
-- Title      : Testbench for design "wb_test_top"
-- Project    : 
-------------------------------------------------------------------------------
-- File       : wb_test_top_tb.vhd
-- Author     : Wojciech Zabołotny  <wzab@wzab.nasz.dom>
-- Company    : 
-- Created    : 2018-11-11
-- Last update: 2018-11-11
-- Platform   : 
-- Standard   : VHDL'93/02
-------------------------------------------------------------------------------
-- Description: 
-------------------------------------------------------------------------------
-- Copyright (c) 2018 
-------------------------------------------------------------------------------
-- Revisions  :
-- Date        Version  Author  Description
-- 2018-11-11  1.0      wzab	Created
-------------------------------------------------------------------------------

library ieee;
use ieee.std_logic_1164.all;

-------------------------------------------------------------------------------

entity wb_test_top_tb is

end entity wb_test_top_tb;
 
-------------------------------------------------------------------------------

architecture test of wb_test_top_tb is

  -- component generics
  constant rdpipename : string := "/tmp/rdpipe";
  constant wrpipename : string := "/tmp/wrpipe";

  -- component ports
  signal rst_i     : std_logic := '1';
  signal clk_sys_i : std_logic;

  -- clock
  signal Clk : std_logic := '1';

begin  -- architecture test

  clk_sys_i <= clk;
  -- component instantiation
  DUT: entity work.wb_test_top
    generic map (
      rdpipename => rdpipename,
      wrpipename => wrpipename)
    port map (
      rst_i     => rst_i,
      clk_sys_i => clk_sys_i);

  -- clock generation
  Clk <= not Clk after 10 ns;

  -- waveform generation
  WaveGen_Proc: process
  begin
    -- insert signal assignments here
    rst_i <= '1';
    wait until Clk = '1';
    wait for 5 ns;
    rst_i <= '0';
    wait;
  end process WaveGen_Proc;

  

end architecture test;

-------------------------------------------------------------------------------

configuration wb_test_top_tb_test_cfg of wb_test_top_tb is
  for test
  end for;
end wb_test_top_tb_test_cfg;

-------------------------------------------------------------------------------
