# Scoped constraints for xpm_cdc_handshake
set slave_clk  [get_clocks -quiet -of [get_ports slave_clk_i]]
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
   set_false_path -to [get_cells resp_s0*_reg*]
   set_max_delay -from $slave_clk -to [get_cells req_m0*_reg*] $master_clk_period -datapath_only
   set_max_delay -from $slave_clk -to [get_cells master_o*_reg*] $master_clk_period -datapath_only
   set_max_delay -from $master_clk -to [get_cells slave_o*_reg*] $slave_clk_period -datapath_only
} elseif {$src_clk != "" && $dest_clk != ""} {
    common::send_msg_id "AGWB_CDC_HANDSHAKE: TCL-1000" "WARNING" "The source and destination clocks are the same. \n     Instance: [current_instance .] \n  This will add unnecessary latency to the design. Please check the design."
}
