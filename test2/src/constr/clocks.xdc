create_clock -period 20.000 -name clk_io_i -waveform {0.000 10.000} [get_ports clk_io_i]
create_clock -period 20.004 -name clk_sys_i -waveform {0.000 10.002} [get_ports clk_sys_i]
set_false_path -to [get_cells rst_sys_0*_reg*]
set_false_path -to [get_cells rst_io_0*_reg*]
