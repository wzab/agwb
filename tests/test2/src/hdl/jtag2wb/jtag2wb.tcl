# Scoped constraints for xpm_cdc_handshake
create_clock -period 50.000 -name clk_jtag -waveform {0.000 25.000} [get_pins BSCANE2_1/TCK]
set slave_clk  [get_clocks -quiet -of [get_pins BSCANE2_1/TCK]]
set master_clk [get_clocks -quiet -of [get_ports master_clk_i]]

set slave_clk_period  [get_property -quiet -min PERIOD $slave_clk]
set master_clk_period [get_property -quiet -min PERIOD $master_clk]

#set xpm_cdc_hs_width [llength [get_cells dest_hsdata_ff_reg[*]]]
#set xpm_cdc_hs_num_s2d_dsync_ff [llength [get_cells xpm_cdc_single_src2dest_inst/syncstages_ff_reg[*]]]

if {$slave_clk == ""} {
    set slave_clk_period 1000
}

if {$master_clk == ""} {
    set master_clk_period 1001
}

if {$slave_clk != $master_clk} {
   set_false_path -to [get_cells s_start_sync*_reg*]
   set_false_path -to [get_cells s_done_sync*_reg*]
   set_max_delay -from $slave_clk -to [get_cells master_o*_reg*] $master_clk_period -datapath_only
   set_max_delay -from $master_clk -to [get_cells dr_shift*_reg*] $slave_clk_period -datapath_only
} elseif {$src_clk != "" && $dest_clk != ""} {
    common::send_msg_id "XPM_CDC_HANDSHAKE: TCL-1000" "WARNING" "The source and destination clocks are the same. \n     Instance: [current_instance .] \n  This will add unnecessary latency to the design. Please check the design for the following: \n 1) Manually instantiated XPM_CDC modules: Xilinx recommends that you remove these modules. \n 2) Xilinx IP that contains XPM_CDC modules: Verify the connections to the IP to determine whether you can safely ignore this message."
}
