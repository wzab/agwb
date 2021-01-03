-------------------------------------------------------------------------------
-- Title      : Wishbone CDC for classic single cycles
-- Project    : 
-------------------------------------------------------------------------------
-- File	      : agwb_pkg.vhd
-- Author     : Wojciech Zabolotny  <wzab01@gmail.com> or <wzab@ise.pw.edu.pl>
-- Company    : 
-- Created    : 2020-01-03
-- Last update: 2021-01-03
-- Platform   :
-- Standard   : VHDL'93/02
-- License    : PUBLIC DOMAIN or Creative Commons CC0
-------------------------------------------------------------------------------
-- Description:
--
-------------------------------------------------------------------------------
-- Copyright (c) 2020
-------------------------------------------------------------------------------
-- Revisions  :
-- Date	       Version	Author	Description
-- 2020-01-03  1.0	WZab	  Created
-------------------------------------------------------------------------------
library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;

library general_cores;
use general_cores.wishbone_pkg.all;

package agwb_pkg is


  constant c_WB_SLAVE_OUT_ERR : t_wishbone_slave_out :=
    (ack => '0', err => '1', rty => '0', stall => '0', dat => c_DUMMY_WB_DATA);

  type t_reps_variants is array (integer range <>) of integer;

end package agwb_pkg;
