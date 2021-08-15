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
  signal outs : t_SYS1_out_regs;
  signal ins : t_SYS1_in_regs;
  signal acks : t_SYS1_ack_regs;  
 
begin  -- architecture rtl

  -- Assign values to the input registers
  g1: for i in 0 to agwb.SYS1_pkg.c_RREG_size - 1 generate
    ins.RREG(i) <= std_logic_vector(to_unsigned(i+3,32));
  end generate g1;
  ins.STATUS <= x"12345678";
  
  SYS1_1: entity agwb.SYS1
    port map (
      slave_i   => wb_s_in,
      slave_o   => wb_s_out,
      out_regs => outs,
      in_regs => ins,
      ack_regs_o => acks,
      rst_n_i   => rst_n_i,
      clk_sys_i => clk_sys_i);
  
end architecture rtl;
