"""
This is the script that generates the VHDL code needed to access
the registers in a hierarchical Wishbone-connected system.

Written by Wojciech M. Zabolotny
(wzab01<at>gmail.com or wzab<at>ise.pw.edu.pl)

Significant improvements by
Michal Kruszewski (mkru<at>protonmail.com)
and
Marek Guminski (marek.guminski<at>gmail.com)

The code is published under LGPL V2 license

This file implements the class handling a Wishbone connected block
"""
import logging as log
import re
import zlib
import expressions as ex

# Define if "volatile" should be used in C headers (if you use _sync_synchronize()
# it may be probably avoided with better results!
XVOLATILE = "volatile" # "volatile" is used
#XVOLATILE = ""  # "volatile" not used

# Special addresses allocated at the begininng of the block address space
# (The testdev - optionally)
# IMPORTANT!
# Please note, that for C header target, the structure is built manually!
# If you change any address below, you have to adjust gen_c_header accordingly!
spec_regs = {
  "id" : 0,
  "ver" : 1,
  "test_rw" : 4,
  "test_wo" : 5,
  "test_ro" : 6,
  "test_tout" : 7,
}

# Template for generation of the VHDL package
TEMPL_PKG = """\
--- This file has been automatically generated
--- by the agwb (https://github.com/wzab/agwb).
--- Please don't edit it manually, unless you really have to do it
library ieee;

use ieee.std_logic_1164.all;
use ieee.numeric_std.all;

library general_cores;
use general_cores.wishbone_pkg.all;

library work;
use work.agwb_pkg.all;

package {p_entity}_pkg is

  constant C_{p_entity}_ADDR_BITS : integer := {p_adr_bits};

{p_generics_consts}

{p_package}
{out_record}
{in_record}
{ack_record}
end {p_entity}_pkg;

package body {p_entity}_pkg is
{p_package_body}
end {p_entity}_pkg;
"""

created_files = {"vhdl": []}

# The function below returns the template for generation of the VHDL code
# There is one argument, describing if it is the top block, that requires
# the multi-master support or not.
def templ_wb(nof_masters):
    res = """\
--- This file has been automatically generated
--- by the agwb (https://github.com/wzab/agwb).
--- Please don't edit it manually, unless you really have to do it
library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;
library general_cores;
use general_cores.wishbone_pkg.all;
library work;
use work.agwb_pkg.all;
use work.{p_entity}_pkg.all;

entity {p_entity} is
  generic (
{p_generics}
{p_ver_id};
    g_registered : integer := 0
  );
  port (
"""
    if nof_masters > 1:
        res += """\
    slave_i : in t_wishbone_slave_in_array({nof_masters}-1 downto 0);
    slave_o : out t_wishbone_slave_out_array({nof_masters}-1 downto 0);
"""
    else:
        res += """\
    slave_i : in t_wishbone_slave_in;
    slave_o : out t_wishbone_slave_out;
"""
    res += """\
{subblk_busses}
{signal_ports}
    rst_n_i : in std_logic;
    clk_sys_i : in std_logic
    );

end {p_entity};

architecture gener of {p_entity} is
{signal_decls}
{testdev_signals}
  -- Internal WB declaration
  signal int_regs_wb_m_o : t_wishbone_master_out;
  signal int_regs_wb_m_i : t_wishbone_master_in;
  signal int_addr : std_logic_vector({reg_adr_bits}-1 downto 0);
  signal wb_up_o : t_wishbone_slave_out_array({nof_masters}-1 downto 0);
  signal wb_up_i : t_wishbone_slave_in_array({nof_masters}-1 downto 0);
  signal wb_up_r_o : t_wishbone_slave_out_array({nof_masters}-1 downto 0);
  signal wb_up_r_i : t_wishbone_slave_in_array({nof_masters}-1 downto 0);
  signal wb_m_o : t_wishbone_master_out_array({nof_subblks}-1 downto 0);
  signal wb_m_i : t_wishbone_master_in_array({nof_subblks}-1 downto 0) := (others => c_WB_SLAVE_OUT_ERR);

  -- Constants
  constant c_address : t_wishbone_address_array({nof_subblks}-1  downto 0) := {p_addresses};
  constant c_mask : t_wishbone_address_array({nof_subblks}-1 downto 0) := {p_masks};
begin
  
{check_assertions}
"""
    if nof_masters == 1:
        res += """\
  wb_up_i(0) <= slave_i;
  slave_o <= wb_up_o(0);
"""
    else:
        res += """\
  wb_up_i <= slave_i;
  slave_o <= wb_up_o;
"""    
    res += """\
  int_addr <= int_regs_wb_m_o.adr({reg_adr_bits}-1 downto 0);

-- Conditional adding of xwb_register   
  gr1: if g_registered = 2 generate
    grl1: for i in 0 to {nof_masters}-1 generate
      xwb_register_1: entity general_cores.xwb_register
      generic map (
        g_WB_MODE => CLASSIC)
      port map (
        rst_n_i  => rst_n_i,
        clk_i    => clk_sys_i,
        slave_i  => wb_up_i(i),
        slave_o  => wb_up_o(i),
        master_i => wb_up_r_o(i),
        master_o => wb_up_r_i(i));
    end generate grl1;
  end generate gr1;

  gr2: if g_registered /= 2 generate
      wb_up_r_i <= wb_up_i;
      wb_up_o <= wb_up_r_o;
  end generate gr2;

-- Main crossbar
  xwb_crossbar_1: entity general_cores.xwb_crossbar
  generic map (
     g_num_masters => {nof_masters},
     g_num_slaves  => {nof_subblks},
     g_registered  => (g_registered = 1),
     g_address     => c_address,
     g_mask        => c_mask
  )
  port map (
     clk_sys_i => clk_sys_i,
     rst_n_i   => rst_n_i,
     slave_i   => wb_up_r_i,
     slave_o   => wb_up_r_o,
     master_i  => wb_m_i,
     master_o  => wb_m_o,
     sdb_sel_o => open
  );

-- Process for register access
  process(clk_sys_i)
  begin
    if rising_edge(clk_sys_i) then
      if rst_n_i = '0' then
        -- Reset of the core
        int_regs_wb_m_i <= c_DUMMY_WB_MASTER_IN;
{control_registers_reset}
      else
        -- Clearing of trigger bits (if there are any)
{trigger_bits_reset}
        -- Normal operation
        int_regs_wb_m_i.rty <= '0';
        int_regs_wb_m_i.ack <= '0';
        int_regs_wb_m_i.err <= '0';
{signals_idle}
        if (int_regs_wb_m_o.cyc = '1') and (int_regs_wb_m_o.stb = '1')
            and (int_regs_wb_m_i.err = '0') and (int_regs_wb_m_i.rty = '0')
            and (int_regs_wb_m_i.ack = '0') then
          int_regs_wb_m_i.err <= '1'; -- in case of missed address
          -- Access, now we handle consecutive registers
          -- Set the error state so it is output when none register is accessed
          int_regs_wb_m_i.dat <= x"A5A5A5A5";
          int_regs_wb_m_i.ack <= '0';
          int_regs_wb_m_i.err <= '1';
{register_access}
{testdev_access}
          if int_addr = {block_id_addr} then
             int_regs_wb_m_i.dat <= {block_id};
             if int_regs_wb_m_o.we = '1' then
                int_regs_wb_m_i.err <= '1';
                int_regs_wb_m_i.ack <= '0';
             else
                int_regs_wb_m_i.ack <= '1';
                int_regs_wb_m_i.err <= '0';
             end if;
          end if;
          if int_addr = {block_ver_addr} then
             int_regs_wb_m_i.dat <= g_ver_id;
             if int_regs_wb_m_o.we = '1' then
                int_regs_wb_m_i.err <= '1';
                int_regs_wb_m_i.ack <= '0';
             else
                int_regs_wb_m_i.ack <= '1';
                int_regs_wb_m_i.err <= '0';
             end if;
          end if;
        end if;
      end if;
    end if;
  end process;
{cont_assigns}
end architecture;
"""
    return res


class GlobalVars(object):
    def __init__(self):
        self.blocks = {}
        self.blackboxes = {}
        self.variants = 0
        self.VER_ID = 0


GLB = GlobalVars()

def blocks():
    return GLB.blocks


def blackboxes():
    return GLB.blackboxes

def get_reps(el):
    """ That function reads the number of repetitions of the block or register
        in different variants, or reads the information about its usage 
        in different variants. It stores the retrieved information in
        the returned object.
    """
    class reps_obj():
        def __init__(self):
            self.force_vec = False
            self.max_reps = 1
            self.reps_variants = [1,]
    r = reps_obj()
    if(el is None):
        return r
    reps = el.get("reps",None)
    used = el.get("used",None)
    if (reps is not None) and (used is not None):
        raise Exception ("In node " + str(el) + " both \"reps\" and \"used\" are defined")
    if (reps is None) and (used is None):
        return r
    if (reps is not None):
        r.force_vec = True
        defs = reps
    else: # used is not None
        r.force_vec = False
        defs = used
    # Now we check how many values are defined and calculate them
    vals = [ex.exprval(v) for v in defs.split(";")]
    r.max_reps = max(vals)
    # In "used" the maximum value is 1
    if used is not None:
        if r.max_reps > 1:
            raise Exception ("In node " + str(el) + " \"used\" has value above 1")
    # The number of variants must be the same in all definitions
    nvars = len(vals)
    if nvars > 1:
        if (GLB.variants > 1) and (nvars != GLB.variants):
            raise Exception ("In node " + str(el) + " number of variants is " + str(nvars) + " but it was earlier set to " + str(GLB.variants))
        GLB.variants = nvars
    r.reps_variants = vals
    return r    

class WbObject(object):
    def is_ignored(self, mode):
        x = self.ignore.split(",")
        z = [y.strip() for y in x]
        return mode in z


class WbField(WbObject):
    def __init__(self, fl, lsb):
        self.name = fl.attrib["name"]
        self.lsb = lsb
        self.size = ex.exprval(fl.attrib["width"])
        self.msb = lsb + self.size - 1
        self.type = fl.get("type", "std_logic_vector")
        self.desc = fl.get("desc", "")
        self.trigger = ex.exprval(fl.get("trigger", "0"))
        self.ignore = fl.get("ignore", "")
        self.default_val = fl.get("default")
        if self.default_val is not None:
            # Convert it to the numerical value
            self.default_val = ex.exprval(self.default_val)

    def def_adjust(self, parent_reg):
        if self.default_val is not None:
            if parent_reg.default_val is None:
                # If there was no default value in the parent, set it to 0
                parent_reg.default_val = 0
            # Now we must set the bits belonging to the bitfield.
            # Create the mask for the bitfield
            or_mask = ((1 << self.size) - 1) << self.lsb
            and_mask = ((1 << 32) - 1) ^ or_mask
            # Check if the default value is not out of limits
            val = self.default_val
            if self.type == "signed":
                if (val < -(1 << (self.size - 1))) or (val >= (1 << (self.size - 1))):
                    raise Exception(
                        "In register "
                        + parent_reg.name
                        + " signed field "
                        + self.name
                        + " with size "
                        + str(self.size)
                        + " bits can't have default value "
                        + str(val)
                    )
                if val < 0:
                    val += 1 << self.size
            else:
                if (val < 0) or (val >= (1 << self.size)):
                    raise Exception(
                        "In register "
                        + parent_reg.name
                        + " field "
                        + self.name
                        + " of type "
                        + self.type
                        + " with size "
                        + str(self.size)
                        + " bits can't have default value "
                        + str(self.default_val)
                    )
            # Shift the corrected value to the right bits
            val <<= self.lsb
            # Set the related bits in the parent register accordingly
            parent_reg.default_val &= and_mask
            parent_reg.default_val |= or_mask & val


class WbReg(WbObject):
    """ The class WbReg describes a single register
    """

    def __init__(self, el, adr):
        """
        The constructor gets the XML node defining the register
        """
        # First we must read the possible sizes of the object
        r = get_reps(el)        
        self.size = r.max_reps
        self.variants = r.reps_variants
        self.force_vec = r.force_vec
        self.regtype = el.tag
        self.type = el.get("type", "std_logic_vector")
        self.stype = el.get("stype", None)
        self.base = adr
        self.name = el.attrib["name"]
        self.size_generic = "g_"+self.name+"_size"
        self.size_constant = "c_"+self.name+"_size"
        self.size_variants = "v_"+self.name+"_size"
        self.trig_clear_constant = "c_"+self.name+"_trig_clear"
        self.mode = el.get("mode", "")
        self.ignore = el.get("ignore", "")
        self.desc = el.get("desc", "")
        self.ack = ex.exprval(el.get("ack", "0"))
        self.stb = ex.exprval(el.get("stb", "0"))
        # Set the width of the register
        self.width = ex.exprval(el.get("width", "32"))
        # Read list of fields
        self.fields = []
        self.free_bit = 0
        for f_l in el.findall("field"):
            fdef = WbField(f_l, self.free_bit)
            self.free_bit += fdef.size
            if self.free_bit > 32:
                raise Exception(
                    "Total width of fields in register "
                    + self.name
                    + " is above 32-bits"
                )
            self.fields.append(fdef)
        # For registers with bitfields we allow enforcing the name of the generated record type
        if self.fields and self.type != "std_logic_vector":
            raise Exception("Register with fields must be of type std_logic_vector")
        if self.free_bit == 0:
            self.free_bit = 32
        # For register with fields, the real width is set by the width of all fields
        if self.fields:
            self.width = self.free_bit
        self.default_val = el.get("default")
        if self.default_val is not None:
            # Convert it to the numerical value
            self.default_val = ex.exprval(self.default_val)
        # Default value may be also modified by default values
        # from bitfields (that have higher priority)
        for f_l in self.fields:
            f_l.def_adjust(self)
        # Now we can adjust the read_mask for the register (used to zero the "trigger"
        # bitfields when reading)
        self.read_mask = 0;
        for f_l in self.fields:
            if f_l.trigger != 0:
                self.read_mask |= ((1 << (f_l.msb + 1)) - 1) ^ ((1 << f_l.lsb) - 1)
        if self.default_val is not None:
            if self.default_val > 2 ** self.free_bit - 1:
                raise Exception(
                    "Default value for " + self.name + " register is too big."
                )
            if (self.size != 1) or (self.force_vec == True):
                self.default = "(others => "
            else:
                self.default = ""
            if self.fields:
                if self.stype is not None:
                    self.default += "to_" + self.stype + "("
                else:
                    self.default += "to_" + self.name + "("
            if self.type == "unsigned":
                self.default += (
                    "to_unsigned(" + str(self.default_val) + "," + str(self.width) + ")"
                )
            elif self.type == "signed":
                self.default += (
                    "to_signed(" + str(self.default_val) + "," + str(self.width) + ")"
                )
            else:
                self.default += (
                    "std_logic_vector(to_unsigned("
                    + str(self.default_val)
                    + ","
                    + str(self.width)
                    + "))"
                )
            if self.fields:
                self.default += ")"
            if (self.size != 1) or (self.force_vec == True):
                self.default += ")"
        else:
            self.default = None

    def var_reps(self,nvar):
        """Function returns the length of the vector of registers
           in the particular variant
        """
        if (nvar is None) or (len(self.variants) == 1):
            return self.size
        else:
            return self.variants[nvar]

    def gen_vhdl(self, parent):
        """
        The method generates the VHDL block responsible for access
        to the registers.
        We append our definitions to the appropriate sections
        in the parrent block.

        We need to generate two sections:
        * Declaration of signals used to input or output the signal,
           and the optional ACK or STB flags
        * Read or write sequence to be embedded in the process
        """
        d_tbr = ""
        d_t = ""
        d_b = ""
        d_i = ""
        d_a = ""
        d_g = "" # definitions of generics
        d_c = "" # Declarations of constant used as default generics values        
        d_t += (
            "constant C_"
            + self.name
            + '_REG_ADDR: unsigned := x"'
            + format(self.base, "08x")
            + '";\n'
        )
        # If read_mask is not 0, we generate a mask for clearing the trigger bits
        if self.read_mask != 0 :        
            d_c += "constant " + self.trig_clear_constant + " : std_logic_vector("
            d_c += str(self.width-1) +' downto 0) := "'
            for i in range(self.width-1,-1,-1):
                if self.read_mask & (1<<i) != 0:
                    d_c += "0"
                else:
                    d_c += "1"
            d_c += '";\n'
        # Generate the generic and constant describing the size of the register vector
        d_c += "constant " + self.size_constant + " : integer := " + str(self.size) +";\n"
        # If there are multiple variants, generate the array with values
        if len(self.variants) > 1:
            d_c += "constant " + self.size_variants + " : t_reps_variants(" + \
                str(GLB.variants - 1) + " downto 0 ) := " + str(tuple(self.variants[::-1])) + ";\n"
        d_g += self.size_generic + " : integer := " + self.size_constant +";\n"
        # Create the assertion
        d_a += "assert " + self.size_generic + " <= " + self.size_constant +\
               " report \"" + self.size_generic + " must be not greater than " +\
               self.size_constant + "=" + str(self.size) + "\" severity failure;\n"
        # Generate the type corresponding to the register
        if self.stype is None:
            tname = "t_" + self.name
        else:
            tname = self.stype
        if not self.fields:
            # Simple register, no fields
            d_t += (
                "subtype "
                + tname
                + " is "
                + self.type
                + "("
                + str(self.width - 1)
                + " downto 0);\n"
            )
        else:
            # Register with fields, we have to create a record
            # If the user specified the name of the type, use it
            d_t += "type " + tname + " is record\n"
            for f_l in self.fields:
                d_t += (
                    "  "
                    + f_l.name
                    + ":"
                    + f_l.type
                    + "("
                    + str(f_l.size - 1)
                    + " downto 0);\n"
                )
            d_t += "end record;\n\n"

            # Conversion function stlv to record
            d_t += (
                "function to_"
                + tname[2:] # Discard "t_"
                + "(x : std_logic_vector) return "
                + tname
                + ";\n"
            )
            d_b += (
                "function to_"
                + tname[2:] # Discard "t_"
                + "(x : std_logic_vector) return "
                + tname
                + " is\n"
            )
            d_b += "  variable res : " + tname + ";\n"
            d_b += "begin\n"
            for f_l in self.fields:
                d_b += (
                    "  res."
                    + f_l.name
                    + " := "
                    + f_l.type
                    + "(x("
                    + str(f_l.msb)
                    + " downto "
                    + str(f_l.lsb)
                    + "));\n"
                )
            d_b += "  return res;\n"
            d_b += "end function;\n\n"

            # Conversion function record to std_logic_vector
            d_t += "function to_slv(x : " + tname + ") return std_logic_vector;\n"
            d_b += "function to_slv(x : " + tname + ") return std_logic_vector is\n"
            d_b += (
                "  variable res : std_logic_vector("
                + str(self.width - 1)
                + " downto 0);\n"
            )
            d_b += "begin\n"
            for f_l in self.fields:
                d_b += (
                    "  res("
                    + str(f_l.msb)
                    + " downto "
                    + str(f_l.lsb)
                    + ") := std_logic_vector(x."
                    + f_l.name
                    + ");\n"
                )
            d_b += "  return res;\n"
            d_b += "end function;\n\n"
        # If this is a vector of registers, create the array types
        if self.force_vec:
            # The unconstrained one
            d_t += (
                "type u"
                + tname
                + "_array is array( natural range <> ) of "
                + tname
                + ";\n"
            )
            # And the constrained one
            d_t += (
                "subtype "
                + tname
                + "_array is u" + tname +
                 "_array(" + self.size_constant + " - 1 downto 0);\n"
            )

        # Append the generated types to the parents package section
        parent.add_templ("p_generics", d_g, 4)
        parent.add_templ("p_generics_consts", d_c, 2)
        parent.add_templ("p_package", d_t, 2)
        parent.add_templ("p_package_body", d_b, 2)
        parent.add_templ("check_assertions", d_a, 2)

        # If the outputs are aggregated, add the type of the signal to the output record type
        if self.regtype == "creg" and parent.out_type is not None:
            if (self.size > 1) or (self.force_vec == True):
                parent.add_templ(
                    "out_record", self.name + " : u" + tname + "_array(" + self.size_constant + " - 1 downto 0);\n", 4
                )
            else:
                parent.add_templ("out_record", self.name + " : " + tname + ";\n", 4)
            if self.stb == 1:
                if (self.size > 1) or (self.force_vec == True):
                    parent.add_templ(
                        "out_record",
                        self.name
                        + "_stb : std_logic_vector("
                        + self.size_constant +" - 1"
                        + " downto 0);\n",
                        4,
                    )
                else:
                    parent.add_templ("out_record", self.name + "_stb : std_logic;\n", 4)
        # If the inputs are aggregated, add the type of the signal to the output record type
        if self.regtype == "sreg" and parent.in_type is not None:
            if (self.size > 1) or (self.force_vec == True):
                parent.add_templ(
                    "in_record", self.name + " : u" + tname + "_array(" + self.size_constant + " - 1 downto 0);\n", 4
                )
            else:
                parent.add_templ("in_record", self.name + " : " + tname + ";\n", 4)
            if self.ack == 1:
                parent.gen_ack = True
                if (self.size > 1) or (self.force_vec == True):
                    parent.add_templ(
                        "ack_record",
                        self.name
                        + " : std_logic_vector("
                        + self.size_constant +" - 1"
                        + " downto 0);\n",
                        4,
                    )
                else:
                    parent.add_templ("ack_record", self.name + " : std_logic;\n", 4)

        # Now generate the entity ports.
        # For simplicity of the code, in case of aggregated outputs or aggregated inputs the port definition
        # is generated, but finally dropped
        d_t = ""
        sfx = "_i"
        sdir = "in "
        if self.regtype == "creg":
            sfx = "_o"
            sdir = "out "
        if self.force_vec:
            d_t = self.name + sfx + " : " + sdir + " u" + tname + "_array(" + self.size_generic + " - 1 downto 0);\n"
        else:
            d_t = self.name + sfx + " : " + sdir + " " + tname + ";\n"
        # Now we generate the STB or ACK ports (if required)
        if self.regtype == "creg" and self.stb == 1:
            if self.force_vec:
                d_t += (
                    self.name
                    + sfx
                    + "_stb : out std_logic_vector("
                    + self.size_generic
                    + " - 1 downto 0);\n"
                )
            else:
                d_t += self.name + sfx + "_stb : out std_logic;\n"
        if self.regtype == "sreg" and self.ack == 1:
            if self.force_vec:
                d_t += (
                    self.name
                    + sfx
                    + "_ack : out std_logic_vector("
                    + self.size_generic
                    + " - 1 downto 0);\n"
                )
            else:
                d_t += self.name + sfx + "_ack : out std_logic;\n"
        # Output the generated port only if the particular register is not
        # aggregated
        if (self.regtype == "creg" and parent.out_type is None) or \
           (self.regtype == "sreg" and parent.in_type is None):
            parent.add_templ("signal_ports", d_t, 4)
        # Generate the intermediate signals for output ports
        # (because they can't be read back)
        # Connect the signals to outputs (without output aggregation) or to
        # the fields in output record (with output aggregation)
        if self.regtype == "creg":
            # Create the intermediate readable signal
            if self.force_vec:
                d_t = "signal int_" + self.name + sfx + " : u" + tname + "_array(" + self.size_generic + " - 1 downto 0)"
            else:
                d_t = "signal int_" + self.name + sfx + " : " + tname
            if self.default is not None:
                d_t += " := " + self.default
            d_t += ";"
            if self.default is not None:
                d_t += " -- Hex value: " + hex(self.default_val)
            d_t += "\n"
            if parent.out_type is None:
                dt2 = self.name + sfx + " <= int_" + self.name + sfx + ";\n"
            else:
                dt2 = (
                    parent.out_name
                    + "."
                    + self.name
                    + " <= int_"
                    + self.name
                    + sfx
                    + ";\n"
                )
            # Create intermediate signals for strobes
            if self.stb == 1:
                if self.force_vec:
                    d_t += (
                        "signal int_"
                        + self.name
                        + sfx
                        + "_stb : std_logic_vector("
                        + self.size_generic
                        + " - 1 downto 0);\n"
                    )
                else:
                    d_t += "signal int_" + self.name + sfx + "_stb : std_logic;\n"
                if parent.out_type is None:
                    dt2 += (
                        self.name + sfx + "_stb <= int_" + self.name + sfx + "_stb;\n"
                    )
                else:
                    dt2 += (
                        parent.out_name
                        + "."
                        + self.name
                        + "_stb <= int_"
                        + self.name
                        + sfx
                        + "_stb;\n"
                    )
            parent.add_templ("signal_decls", d_t, 2)
            parent.add_templ("cont_assigns", dt2, 2)
        # Connect the register inputs to the input record
        
        # Reset control registers
        if self.regtype == "creg":
            if self.default is not None:
                r_t = (
                    "int_"
                    + self.name
                    + sfx
                    + " <= "
                    + self.default
                    + "; -- Hex value: "
                    + hex(self.default_val)
                    + "\n"
                )
                parent.add_templ("control_registers_reset", r_t, 8)
        # Generate the signal assignment in the process
        d_t = ""
        if not self.force_vec:
            # If it is a single oject, add comment why we use for-loop without indexing
            d_t += '\n'
            d_t += '-- That\'s a single register that may be present (size=1) or not (size=0).\n'
            d_t += '-- The "for" loop works like "if".\n'
            d_t += '-- That\'s why we do not index the register inside the loop.\n'
        d_t += (
            'for i in 0 to '
            + self.size_generic + ' - 1 loop\n'
        )
        # We prepare the index string used in case if this is a vector of registers
        if self.force_vec:
            ind = "( i )"
        else:
            ind = ""
        d_t += (
            '  if int_addr = std_logic_vector(to_unsigned('
            + str(self.base) +  ' + i, '  + str(parent.reg_adr_bits)
            + ")) then\n"
        )
        d_i = ""
        # The conversion functions
        if not self.fields:
            conv_fun = "std_logic_vector"
            iconv_fun = self.type
        elif self.stype is not None:
            conv_fun = "to_slv"
            iconv_fun = "to_" + self.stype[2:] # Discard "t_"
        else:
            conv_fun = "to_slv"
            iconv_fun = "to_" + self.name
        # Read access
        if self.regtype == "sreg":
            # First initialize the whole return value with zeroes
            d_t += "    int_regs_wb_m_i.dat <= (others => '0');\n"
            # Set the right input signal name
            if parent.in_type is None:
                sig_name = self.name + "_i"
            else:
                sig_name = parent.in_name + "." + self.name
            # Now set the used bits with correct values
            d_t += (
                "    int_regs_wb_m_i.dat("
                + str(self.width - 1)
                + " downto 0) <= "
                + conv_fun
                + "("
                + sig_name
                + ind
                + ");\n"
            )
            if self.ack == 1:
                # Set the right ACK signal name
                if parent.ack_type is None:
                    ack_name = self.name + sfx + "_ack"
                else:
                    ack_name = parent.ack_name + "." + self.name 
                d_t += "    if int_regs_wb_m_i.ack = '0' then\n"
                # We shorten the ACK to a single clock
                d_t += "       " + ack_name + ind + " <= '1';\n"
                d_t += "    end if;\n"
                # Add clearing of ACK signal at the begining of the process
                if self.force_vec:
                    d_i += ack_name + " <= (others => '0');\n"
                else:
                    d_i += ack_name + " <= '0';\n"
        else:
            # First initialize the whole return value with zeroes
            d_t += "    int_regs_wb_m_i.dat <= (others => '0');\n"
            # Now set the used bits with correct values
            d_t += (
                "    int_regs_wb_m_i.dat("
                + str(self.width - 1)
                + " downto 0) <= "
                + conv_fun
                + "(int_"
                + self.name
                + sfx
                + ind
                + ")")
            if self.read_mask != 0 :
                d_t += " and " + self.trig_clear_constant
                # Additionally we add clearing the trigger bits
                # to the trigger_bits_reset section
                if not self.force_vec:
                    # Add comment why we use for-loop without indexing
                    d_tbr += '\n'
                    d_tbr += '-- That\'s a single register that may be present (size=1) or not (size=0).\n'
                    d_tbr += '-- The "for" loop works like "if".\n'
                    d_tbr += '-- That\'s why we do not index the register inside the loop.\n'
                d_tbr += (
                    'for i in 0 to '
                    + self.size_generic + ' - 1 loop\n'
                    "   int_" + self.name + sfx + ind + " <= "
                    + iconv_fun + "( agwb_and("+conv_fun+"("
                    + "int_" + self.name + sfx + ind + "), " + self.trig_clear_constant + "));\n"
                    +'end loop;\n'
                    )
            d_t += ";\n"
        # Write access
        if self.regtype == "creg":
            d_t += "    if int_regs_wb_m_o.we = '1' then\n"
            d_t += (
                "      int_"
                + self.name
                + "_o"
                + ind
                + " <= "
                + iconv_fun
                + "(int_regs_wb_m_o.dat("
                + str(self.width - 1)
                + " downto 0));\n"
            )
            if self.stb == 1:
                d_t += "      if int_regs_wb_m_i.ack = '0' then\n"
                # We shorten the STB to a single clock
                d_t += "        int_" + self.name + sfx + "_stb" + ind + " <= '1';\n"
                d_t += "      end if;\n"
                # Add clearing of STB signal at the begining of the process
                if self.force_vec:
                    d_i += "int_" + self.name + sfx + "_stb <= (others =>'0');\n"
                else:
                    d_i += "int_" + self.name + sfx + "_stb <= '0';\n"
            d_t += "    end if;\n"
        d_t += "    int_regs_wb_m_i.ack <= '1';\n"
        d_t += "    int_regs_wb_m_i.err <= '0';\n"
        d_t += "  end if;\n"
        d_t += "end loop; -- "  + self.size_generic + "\n"
        parent.add_templ("register_access", d_t, 10)
        parent.add_templ("signals_idle", d_i, 8)
        parent.add_templ("trigger_bits_reset", d_tbr, 8)

    def gen_amap_xml(self, reg_base, nvar = None):
        res = ""
        r_n = self.var_reps(nvar)     
        if r_n > 0:
            adr = reg_base + self.base
            rname = self.name
            # If this is the vector, add additional attributes
            if self.force_vec:
                rvec = ' nelems="'+str(r_n)+'" elemoffs="1" '
            else:
                rvec = ""
            # Set permissions
            if self.regtype == "creg":
                perms = "rw"
            elif self.regtype == "sreg":
                perms = "r"
            else:
                raise Exception("Unknown type of register")
            # Pass the "mode" attribute to the generated IPbus XML
            s_mode = ""
            if self.mode != "":
                s_mode = ' mode="' + self.mode + '"'
            # Generate the mask for register with width below 32 bits
            s_mask = ""
            if self.width < 32:
                maskval = (1 << self.width) - 1
                s_mask = ' mask="0x' + format(maskval, "08x") + '"'            
            # Finally the format of the description depends on the presence of bitfields
            if not self.fields:
                res += (
                    '  <register id="'
                    + rname
                    + '" address="0x'
                    + format(adr, "08x")
                    + '"'
                    + rvec
                    + ' permission="'
                    + perms
                    + '"'
                    + s_mode
                    + s_mask
                    + "/>\n"
                )
            else:
                res += (
                    '  <register id="'
                    + rname
                    + '" address="0x'
                    + format(adr, "08x")
                    + '"'
                    + rvec
                    + ' permission="'
                    + perms
                    + '"'
                    + s_mode
                    + ">\n"
                )
                for b_f in self.fields:
                    maskval = ((1 << (b_f.msb + 1)) - 1) ^ ((1 << b_f.lsb) - 1)
                    mask = format(maskval, "08x")
                    res += '    <field id="' + b_f.name + '" mask="0x' + mask + '"/>\n'
                res += "  </register>\n"

        return res

    def gen_ipbus_xml(self, reg_base):
        # The generated code depends on the fact it is a single register or the vector of registers
        res = ""
        for r_n in range(0, self.size):
            adr = reg_base + self.base + r_n
            # The name format depends whether its a single register or an item in a vector
            if self.force_vec:
                rname = self.name + "[" + str(r_n) + "]"
            else:
                rname = self.name
            # Set permissions
            if self.regtype == "creg":
                perms = "rw"
            elif self.regtype == "sreg":
                perms = "r"
            else:
                raise Exception("Unknown type of register")
            # Pass the "mode" attribute to the generated IPbus XML
            s_mode = ""
            if self.mode != "":
                s_mode = ' mode="' + self.mode + '"'

            # Generate the mask for register with width below 32 bits
            s_mask = ""
            if self.width < 32:
                maskval = (1 << self.width) - 1
                s_mask = ' mask="0x' + format(maskval, "08x") + '"'

            # Finally the format of the description depends on the presence of bitfields
            if not self.fields:
                res += (
                    '  <node id="'
                    + rname
                    + '" address="0x'
                    + format(adr, "08x")
                    + '" permission="'
                    + perms
                    + '"'
                    + s_mode
                    + s_mask
                    + "/>\n"
                )
            else:
                res += (
                    '  <node id="'
                    + rname
                    + '" address="0x'
                    + format(adr, "08x")
                    + '" permission="'
                    + perms
                    + '"'
                    + s_mode
                    + ">\n"
                )
                for b_f in self.fields:
                    maskval = ((1 << (b_f.msb + 1)) - 1) ^ ((1 << b_f.lsb) - 1)
                    mask = format(maskval, "08x")
                    res += '    <node id="' + b_f.name + '" mask="0x' + mask + '"/>\n'
                res += "  </node>\n"

        return res

    def gen_c_header(self, reg_base, block_name):
        res = "  " + XVOLATILE + " uint32_t " + self.name
        head = ""
        if self.fields:
            # There are bitfields, so we need to generate functions needed to access them
            base_type = "agwb_" + block_name
            for b_f in self.fields:
                # Below we generate a set of masks and shift values needed
                # to extract or to set the appropriate value...
                base_name = base_type + "_" + self.name + "_" + b_f.name
                fshift = b_f.lsb
                fmask = (1 << (b_f.msb - b_f.lsb + 1)) - 1
                fvalmask = 0xFFFFFFFF - (fmask << b_f.lsb)
                fsignmask = 1 << (b_f.msb - b_f.lsb)
                fsignext = ((1 << (31 - (b_f.msb - b_f.lsb))) - 1) << b_f.msb
                if b_f.type == "signed":
                    # Function for getting the value
                    head += (
                        "static inline int32_t "
                        + base_name
                        + "_get(uint32_t * ptr) { \n"
                    )
                    head += (
                        "  int32_t res = (((* ptr) >> "
                        + hex(fshift)
                        + ") & "
                        + hex(fmask)
                        + ");\n"
                    )
                    head += (
                        "  return (res & "
                        + hex(fsignmask)
                        + ") ? (res | "
                        + hex(fsignext)
                        + ") : res;\n };\n"
                    )
                    # Function for setting the value
                    head += (
                        "static inline void "
                        + base_name
                        + "_set(uint32_t * ptr, int32_t val) { \n"
                    )
                    head += (
                        "  * ptr = ((* ptr) & "
                        + hex(fvalmask)
                        + ") | ((val & "
                        + hex(fmask)
                        + ") << "
                        + hex(fshift)
                        + ");\n"
                    )
                    head += "};\n"
                else:
                    # Function for getting the value
                    head += (
                        "static inline uint32_t "
                        + base_name
                        + "_get(uint32_t * ptr) { \n"
                    )
                    head += (
                        "  return ((* ptr) >> "
                        + hex(fshift)
                        + ") & "
                        + hex(fmask)
                        + ";\n};\n"
                    )
                    # Function for setting the value
                    head += (
                        "static inline void "
                        + base_name
                        + "_set(uint32_t * ptr, uint32_t val) { \n"
                    )
                    head += (
                        "  * ptr = ((* ptr) & "
                        + hex(fvalmask)
                        + ") | ((val & "
                        + hex(fmask)
                        + ") << "
                        + hex(fshift)
                        + ");\n"
                    )
                    head += "};\n"
        # The generated code depends on the fact it is a single register or the vector of registers
        if self.force_vec:
            res += "[" + str(self.size) + "];\n"
        else:
            res += ";\n"
        return res, head

    def gen_forth(self, reg_base, parent):
        # The generated code depends on the fact it is a single register or the vector of registers
        cdefs = ""
        if self.is_ignored("forth"):
            return cdefs
        adr = reg_base + self.base
        # The name format depends whether its a single register or an item in a vector
        if self.force_vec:
            node = parent + "#" + self.name
            cdefs += ": " + node + " " + parent + " + $" + format(adr, "x") + " + ;\n"
        else:
            node = parent + "_" + self.name
            cdefs += ": " + node + " " + parent + " $" + format(adr, "x") + " + ;\n"
        if self.fields:
            for b_f in self.fields:
                maskval = ((1 << (b_f.msb + 1)) - 1) ^ ((1 << b_f.lsb) - 1)
                cdefs += (
                    ": "
                    + node
                    + "."
                    + b_f.name
                    + " "
                    + node
                    + " $"
                    + format(maskval, "x")
                    + " $"
                    + format(b_f.lsb, "x")
                    + " ;\n"
                )
        return cdefs

    def gen_python(self, reg_base, nvar = None):
        sp8 = 8 * " "
        sp12 = 12 * " "
        res = ""
        r_n = self.var_reps(nvar)
        if r_n > 0:
            if self.force_vec:
                # Vector of registers
                res += (
                    sp8
                    + "'"
                    + self.name
                    + "':("
                    + hex(reg_base + self.base)
                    + ","
                    + str(self.size)
                    + ",("
                )
            else:
                # Single register
                res += sp8 + "'" + self.name + "':(" + hex(reg_base + self.base) + ",("
            if self.regtype == "sreg":
                res += "agwb.StatusRegister,"
            elif self.regtype == "creg":
                res += "agwb.ControlRegister,"
            else:
                raise Exception("Incorrect type of register:" + self.regtype)
            if not self.fields:
                # No bitfields
                res += ")),\n"
            else:
                # Handle bitfields
                res += "\n" + sp8 + "{\\\n"
                for f_l in self.fields:
                    res += (
                        sp12
                        + "'"
                        + f_l.name
                        + "':agwb.BitField("
                        + str(f_l.msb)
                        + ","
                        + str(f_l.lsb)
                        + ","
                    )
                    if self.type == "signed":
                        res += "True"
                    else:
                        res += "False"
                    res += "),\\\n"
                res += sp8 + "})),\n"
        return res

    def gen_html(self, base, name):
        res = ""
        res += (
            "<details><summary>"
            + hex(base + self.base)
            + ": "
            + name
            + "."
            + self.name
            + "</p>"
        )
        res += "</summary>"
        res += "<p>" + self.desc + "</p>"
        if self.fields:
            res += "<ul>"
            for f_l in self.fields:
                res += (
                    "<li>"
                    + str(f_l.msb)
                    + "-"
                    + str(f_l.lsb)
                    + ": "
                    + f_l.name
                    + "<br>"
                )
                res += f_l.desc + "</li>"
            res += "</ul>"
        res += "</details>"
        return res


class WbArea(WbObject):
    """ The class representing the address area
    """

    def __init__(self, size, name, obj, oreps, ignore=""):
        self.name = name
        self.size_generic = "g_" + self.name+ "_size"
        self.size_constant = "c_" + self.name+ "_size"
        self.size_variants = "v_" + self.name+ "_size"
        self.size = size
        self.obj = obj
        self.adr = 0
        self.mask = 0
        self.total_size = 0
        self.reps = oreps.max_reps
        self.variants = oreps.reps_variants
        self.force_vec = oreps.force_vec
        self.ignore = ignore

    def var_reps(self,nvar):
        """Function returns the number of repetitions of objects in the area
           in the particular variant
        """
        if (nvar is None) or (len(self.variants) == 1):
            return self.reps
        else:
            return self.variants[nvar]

    def sort_adr(self):
        return self.adr

    def sort_key(self):
        return self.size


class WbBlackBox(WbObject):
    def __init__(self, el):
        self.name = el.attrib["type"]
        self.desc = el.get("desc", "")
        self.adr_bits = ex.exprval(el.attrib["addrbits"])
        self.xmlpath = el.get("xmlpath", "")
        self.addr_size = 1 << self.adr_bits
        # We do not store "reps" in the instance, as it may depend on the instance!

    def gen_forth(self, parent):
        # We do not need to generate any special words for blackboxes
        return ""

    def gen_c_header(self):
        # Here we need to create a dummy header, that just fills the generated structure
        log.debug("Creating C header:" + self.name + "\n")
        res = "#ifndef __" + self.name + "__INC_H\n"
        res += "#define __" + self.name + "__INC_H\n"
        res += "typedef struct {\n"
        res += "  " + XVOLATILE + " uint32_t filler[" + str(self.addr_size) + "];\n"
        res += "}  __attribute__((aligned(4))) " + "agwb_" + self.name + ";\n"
        res += "#endif\n"
        with open(GLB.C_HEADER_PATH + "/agwb_" + self.name + ".h", "w") as f_o:
            f_o.write(res)

    def gen_python(self, nvar = None):
        """ This function generates the class providing access
        to the blackbox from the Python code.
        Currently the blackbox is simply handled as a vector
        of registers reg[size].
        """
        sp4 = 4 * " "
        sp8 = 8 * " "
        res = "\nclass " + self.name + "(agwb.Block):\n"
        res += sp4 + "x__is_blackbox = True\n"
        res += sp4 + "x__size = " + str(self.addr_size) + "\n"
        res += sp4 + "x__fields = {\n"
        res += (
            sp8
            + "'reg':("
            + hex(0)
            + ","
            + str(self.addr_size)
            + ",(agwb.ControlRegister,))\n"
        )
        res += sp4 + "}\n\n"
        return res

    def gen_html(self, base, name):
        res = "Address: " + hex(base) + " Name: " + name + "<br>"
        return res


class WbBlock(WbObject):
    def __init__(self, el):
        """
        The constructor takes an XML node that describes the block
        It also calculates the number of registers, and creates
        the description of the record
        """
        self.used = False  # Mark the block as not used yet
        self.templ_dict = {}
        self.name = el.attrib["name"]
        self.id_val = zlib.crc32(bytes(self.name.encode("utf-8")))
        self.ver_full = 0
        self.ver_var = {}
        self.desc = el.get("desc", "")
        self.testdev_ena = ex.exprval(el.get("testdev_ena", "0"))
        self.ignore = el.get("ignore", "")
        self.reserved = ex.exprval(el.get("reserved", "0"))
        # We check if the outputs from the registers should be aggregated
        self.aggregate_outs = el.get("aggr_outs", "0")
        # We check if the inputs to the registers should be aggregated
        self.aggregate_ins = el.get("aggr_ins", "0")
        self.gen_ack = False
        # We prepare the list of address areas
        self.areas = []
        # We prepare the table for storing the registers.
        self.regs = []
        if self.testdev_ena != 0:
            self.free_reg_addr = 8  # We reserve eight addresses for ID, VER and TEST DEVICE
        else:
            self.free_reg_addr = 2  # The first free address after ID & VER
        # Prepare the list of subblocks
        self.subblks = []
        self.N_MASTERS = 1
        # Prepare the counter used for if-generate labels for sub-bus asignment
        self.bg_nr = 0
        for child in el.findall("*"):
            # Now for registers we allocate addresses in order
            # We don't do alignment (yet)
            if child.tag == "creg":
                # This is a control register
                reg = WbReg(child, self.free_reg_addr)
                self.free_reg_addr += reg.size
                self.regs.append(reg)
            elif child.tag == "sreg":
                # This is a status register
                reg = WbReg(child, self.free_reg_addr)
                self.free_reg_addr += reg.size
                self.regs.append(reg)
            elif child.tag == "subblock":
                # This is a subblock definition
                # We only add it to the list, the addresses can't be allocated yet
                self.subblks.append(child)
            elif child.tag == "blackbox":
                # This is a blackbox subblock definition
                # We only add it to the list, the addresses can't be allocated yet
                self.subblks.append(child)
            else:
                # Unknown child
                raise Exception("Unknown node in block: " + el.name)
        # After that procedure, the field free_reg_addr contains
        # the length of the block of internal registers
        self.reg_adr_bits = (self.free_reg_addr - 1).bit_length()

    def analyze(self):
        # Add the length of the local addresses to the list of areas
        self.areas.append(WbArea(self.free_reg_addr, "int_regs", None, get_reps(None)))
        # Scan the subblocks
        for sblk in self.subblks:
            if sblk.tag == "subblock":
                # @!@ Here we must to correct something! The name of the subblock
                # Is currently lost. We must to decide how it should be passed
                # To the generated code@!@
                b_l = GLB.blocks[sblk.attrib["type"]]
                # If the subblock was not analyzed yet, analyze it now
                if not b_l.areas:
                    b_l.analyze()
                    # Now we can be sure, that it is analyzed, so we can
                    # add its address space to ours.
                # Check if this is a vector of subblocks
                oreps = get_reps(sblk)
                ignore = sblk.get("ignore", "")
                # Now recalculate the size of the area, considering possible
                # block repetitions
                addr_size = b_l.addr_size * oreps.max_reps
                self.areas.append(
                    WbArea(addr_size, sblk.get("name"), b_l, oreps, ignore)
                )
            elif sblk.tag == "blackbox":
                # We don't need to analyze the blackbox. We allready have its
                # address area size.
                if not sblk.attrib["type"] in GLB.blackboxes:
                    GLB.blackboxes[sblk.attrib["type"]] = WbBlackBox(sblk)
                b_l = GLB.blackboxes[sblk.attrib["type"]]
                oreps = get_reps(sblk)
                ignore = sblk.get("ignore", "")
                addr_size = b_l.addr_size * oreps.max_reps
                self.areas.append(
                    WbArea(addr_size, sblk.get("name"), b_l, oreps, ignore)
                )
            else:
                raise Exception("Unknown type of subblock")
        # In that version we use a more complex address allocation scheme
        # 1. The total size of the address space is allocated (including the reserved area)
        #    The calculated size of the address space is adjusted to the 2^N
        # 2. The registers are allocated at the begining of the address space,
        #    after the reserved area.
        # 3. The blocks are allocated starting freom the end of the address
        #
        # First calculate the total length of address space
        #
        # We use the simplest algorithm - all blocks are sorted,
        # their size is rounded up to the nearest power of 2
        # They are allocated in order.
        cur_size = self.reserved
        self.areas.sort(key=WbArea.sort_key, reverse=True)
        for a_r in self.areas:
            a_r.adr_bits = (a_r.size - 1).bit_length()
            a_r.total_size = 1 << a_r.adr_bits
            # Now we shift the position of the next block
            cur_size += a_r.total_size
            log.debug("added size:" + str(a_r.total_size))
        # We must adjust the address space to the power of two
        self.adr_bits = (cur_size - 1).bit_length()
        self.addr_size = 1 << self.adr_bits
        # Now we allocate the base addresses
        cur_top = self.addr_size
        for a_r in self.areas:
            if a_r.obj is None:
                # This is the register block, so we allocate it at the begining, after the reserved area
                self.reg_base = self.reserved
                a_r.adr = self.reserved
            else:
                cur_top -= a_r.total_size
                a_r.adr = cur_top
        self.used = True
        # In fact, here we should be able to generate the HDL code
        log.debug("analyze: " + self.name + " addr_size:" + str(self.addr_size))

    def add_templ(self, templ_key, value, indent):
        """ That function adds the new text to the dictionary
            used to fill the templates for code generation.
        """
        if templ_key not in self.templ_dict:
            self.templ_dict[templ_key] = ""
        # Now we add all lines from value, providing the appropriate indentation
        for l_n in re.findall(r".*\n?", value)[:-1]:
            if l_n != "":
                self.templ_dict[templ_key] += indent * " " + l_n

    def set_templ(self, templ_key, value):
        """ That function sets the code template in the dictionary 
            to the given value.
        """
        self.templ_dict[templ_key] = value
                
    def create_addr(self,adr):
        return '"' + format(adr, "0" + str(self.reg_adr_bits) + "b") + '"'

    def gen_vhdl(self):
        # To fill the template, we must to set the following values:
        # p_entity, valid_bits

        # subblk_busses, signal_ports, signal_decls
        # nof_subblks,
        # subblk_assignments,
        # n_slaves,
        # p_addresses, p_masks
        # block_id, block_ver - to verify that design matches the software

        # First - generate code for registers
        # We give empty declaration in case if the block does not contain
        # any registers
        self.add_templ("p_generics", "", 0)
        self.add_templ("p_ver_id", "", 0)
        self.add_templ("p_generics_consts", "", 0)
        self.add_templ("p_package", "", 0)
        self.add_templ("p_package_body", "", 0)
        self.add_templ("check_assertions", "", 0)
        self.add_templ("signal_decls", "", 0)
        self.add_templ("control_registers_reset", "", 0)
        self.add_templ("trigger_bits_reset", "", 0)
        self.add_templ("register_access", "", 0)
        self.add_templ("testdev_access", "", 0)
        self.add_templ("testdev_signals", "", 0)
        self.add_templ("subblk_busses", "", 0)
        self.add_templ("signal_ports", "", 0)
        self.add_templ("signals_idle", "", 0)
        self.add_templ("out_record", "", 0)
        self.add_templ("in_record", "", 0)
        self.add_templ("ack_record", "", 0)
        if self.testdev_ena != 0:
            d_t = "-- Test device signals\n"
            d_t += "signal sig_testdev_rw : std_logic_vector(31 downto 0) := (others => '0');\n"
            d_t += "signal sig_testdev_rowo : std_logic_vector(31 downto 0) := (others => '0');\n"
            self.add_templ("testdev_signals",d_t,2);
            d_t = """
if int_addr = """ + self.create_addr(spec_regs["test_rw"]) + """ then -- test_rw
   int_regs_wb_m_i.dat <= sig_testdev_rw;
   if int_regs_wb_m_o.we = '1' then
      sig_testdev_rw <= std_logic_vector(int_regs_wb_m_o.dat);
   end if;
   int_regs_wb_m_i.ack <= '1';
   int_regs_wb_m_i.err <= '0';
end if;
if int_addr = """ + self.create_addr(spec_regs["test_wo"]) + """ then -- test_wo
   if int_regs_wb_m_o.we = '1' then
      sig_testdev_rowo <= std_logic_vector(int_regs_wb_m_o.dat);
      int_regs_wb_m_i.ack <= '1';
      int_regs_wb_m_i.err <= '0';
   else
      int_regs_wb_m_i.ack <= '0';
      int_regs_wb_m_i.err <= '1';
   end if;
end if;
if int_addr = """ + self.create_addr(spec_regs["test_ro"]) + """ then -- test_ro
   if int_regs_wb_m_o.we = '1' then
      int_regs_wb_m_i.ack <= '0';
      int_regs_wb_m_i.err <= '1';
   else
      int_regs_wb_m_i.dat <= sig_testdev_rowo;
      int_regs_wb_m_i.ack <= '1';
      int_regs_wb_m_i.err <= '0';
   end if;
end if;
if int_addr = """ + self.create_addr(spec_regs["test_tout"]) + """ then -- test_tout
     int_regs_wb_m_i.ack <= '0';
     int_regs_wb_m_i.err <= '0';
end if;
"""
            self.add_templ("testdev_access",d_t,10);
        # If the outputs must be aggregated in a single record,
        # we will generate a type for that record instead of output ports
        log.debug(self.name)
        # Generate the block version id constants
        d_c = 'constant c_'+self.name+'_ver_id : std_logic_vector(31 downto 0) := '
        d_c += 'x"' + format(self.ver_full, "08x") + '";\n'
        # If the block has variants, generate the ID table
        if self.ver_var:
            d_c += "constant v_"+self.name+"_ver_id : t_ver_id_variants("
            d_c += str(GLB.variants - 1) +' downto 0) := ('
            for i in range(GLB.variants-1,-1,-1): # Reverse order due to "downto"
                if i != GLB.variants-1:
                    d_c += ","
                d_c += 'x"' + format(self.ver_var[i], "08x") + '"'
            d_c += ");\n"
        else:
            d_c += "constant v_"+self.name+"_ver_id : t_ver_id_variants(0 downto 0) := ("
            d_c += '0 => x"' + format(self.ver_full, "08x") + '");\n'
        self.add_templ("p_generics_consts", d_c, 2)        
        if self.aggregate_outs != "0":
            self.out_type = "t_" + self.name + "_out_regs"
            self.add_templ("out_record", "type " + self.out_type + " is record\n", 2)
            self.out_name = "out_regs"
        else:
            self.out_type = None
            self.out_name = None
        if self.aggregate_ins != "0":
            self.in_type = "t_" + self.name + "_in_regs"
            self.add_templ("in_record", "type " + self.in_type + " is record\n", 2)
            self.in_name = "in_regs"
            self.ack_type = "t_" + self.name + "_ack_regs"
            self.add_templ("ack_record", "type " + self.ack_type + " is record\n", 2)
            self.ack_name = "ack_regs_o"
        else:
            self.in_type = None
            self.in_name = None
            self.ack_type = None
            self.ack_name = None
        for reg in self.regs:
            # generate
            reg.gen_vhdl(self)
        # Generate code for connection of all areas
        ar_adr_bits = []
        ar_addresses = []
        n_ports = 0
        d_t = ""
        d_a = "" # The assertions
        d_g = "" # Declarations of generics
        d_c = "" # Declarations of constant used as default generics values
        for a_r in self.areas:
            # Generate the size generic and constant but not for internal registers
            if a_r.obj != None:
                d_g += a_r.size_generic + " : integer := " + a_r.size_constant + ";\n"
                d_c += "constant " + a_r.size_constant + " : integer := " + str(a_r.reps) + ";\n"
                # If there are multiple variants, generate the array with values
                if len(a_r.variants) > 1:
                    d_c += "constant " + a_r.size_variants + " : t_reps_variants( " + \
                        str(GLB.variants - 1) +  " downto 0 ) := " + str(tuple(a_r.variants[::-1])) + ";\n"
                # Create the assertion
                d_a += "assert " + a_r.size_generic + " <= " + a_r.size_constant +\
                   " report \"" + a_r.size_generic + " must be not greater than " +\
                   a_r.size_constant + "=" + str(a_r.reps) + "\" severity failure;\n"
            if (a_r.reps == 1) and (a_r.force_vec == False):
                a_r.first_port = n_ports
                a_r.last_port = n_ports
                n_ports += 1
                ar_addresses.append(a_r.adr)
                ar_adr_bits.append(a_r.adr_bits)
                if a_r.obj is None:
                    # For internal registers simply connect the bus
                    d_t = (
                        "wb_m_i(" + str(a_r.first_port) + ") <= " + a_r.name + "_wb_m_i;\n"
                    )
                    d_t += (
                        a_r.name + "_wb_m_o  <= " + "wb_m_o(" + str(a_r.first_port) + ");\n"
                    )
                if a_r.obj != None:
                    # For subblocks generate the entity port 
                    d_t = a_r.name + "_wb_m_o : out t_wishbone_master_out;\n"
                    d_t += a_r.name + "_wb_m_i : in t_wishbone_master_in := c_WB_SLAVE_OUT_ERR;\n"
                    self.add_templ("subblk_busses", d_t, 4)
                    # conditionally (due to possible 'used' attribute) generate the signal assignment
                    self.bg_nr += 1
                    d_t = "bg" + str(self.bg_nr) + ": if " + a_r.size_generic + " > 0 generate\n"                
                    d_t += (
                        "  wb_m_i(" + str(a_r.first_port) + ") <= " + a_r.name + "_wb_m_i;\n"
                    )
                    d_t += (
                        "  " + a_r.name + "_wb_m_o  <= " + "wb_m_o(" + str(a_r.first_port) + ");\n"
                    )
                    d_t += "end generate; -- " + a_r.size_generic + "\n"                
                self.add_templ("cont_assigns", d_t, 2)
            else:
                # The area is associated with the vector of subblocks
                a_r.first_port = n_ports
                a_r.last_port = n_ports + a_r.reps - 1
                n_ports += a_r.reps
                # generate the entity port
                d_t = (
                    a_r.name
                    + "_wb_m_o : out t_wishbone_master_out_array( "
                    + a_r.size_generic
                    + " - 1 downto 0 );\n"
                )
                d_t += (
                    a_r.name
                    + "_wb_m_i : in t_wishbone_master_in_array( "
                    + a_r.size_generic
                    + " - 1 downto 0 ) := ( others => c_WB_SLAVE_OUT_ERR);\n"
                )
                self.add_templ("subblk_busses", d_t, 4)
                # Now we have to assign addresses and masks for each subblock
                base = a_r.adr
                for i in range(0,a_r.reps):
                    ar_addresses.append(base)
                    base += a_r.obj.addr_size
                    ar_adr_bits.append(a_r.obj.adr_bits)
                # The bus assignment must be generated conditionally in a loop (depending on generics)
                self.bg_nr += 1
                d_t = "bg" + str(self.bg_nr) + ": for i in 0 to " + a_r.size_generic + " - 1 generate\n"                
                d_t += (
                    "  wb_m_i("
                    + str(a_r.first_port)
                    + " + i) <= "
                    + a_r.name
                    + "_wb_m_i(i);\n"
                )
                d_t += (
                    "  "
                    + a_r.name
                    + "_wb_m_o(i)  <= "
                    + "wb_m_o("
                    + str(a_r.first_port)
                    + " + i);\n"
                )
                d_t += "end generate; -- for " + a_r.size_generic + "\n"
                self.add_templ("cont_assigns", d_t, 2)
        self.add_templ("check_assertions",d_a,2)
        self.add_templ("p_generics",d_g,4)
        self.add_templ("p_generics_consts",d_c,2)
        # Now generate vectors with addresses and masks
        adrs = "("
        masks = "("
        for i in range(0, n_ports):
            if i > 0:
                adrs += ","
                masks += ","
            adrs += str(i) + '=>"' + format(ar_addresses[i], "032b") + '"'
            # Calculate the mask
            maskval = ((1 << self.adr_bits) - 1) ^ ((1 << ar_adr_bits[i]) - 1)
            masks += str(i) + '=>"' + format(maskval, "032b") + '"'
        adrs += ")"
        masks += ")"
        # Generate the register address for special registers
        self.add_templ(
            "block_id_addr",
            self.create_addr(spec_regs["id"]),
            0,
        )
        self.add_templ(
            "block_ver_addr",
            self.create_addr(spec_regs["ver"]),
            0,
        )
        self.add_templ("reg_adr_bits", str(self.reg_adr_bits), 0)
        self.add_templ("p_adr_bits", str(self.adr_bits), 0)
        self.add_templ("block_id", 'x"' + format(self.id_val, "08x") + '"', 0)
        self.add_templ("p_ver_id", "g_ver_id : std_logic_vector(31 downto 0)"
                       " := c_" + self.name + "_ver_id", 4)
        self.add_templ("p_addresses", adrs, 0)
        self.add_templ("p_masks", masks, 0)
        self.add_templ("nof_subblks", str(n_ports), 0)
        self.add_templ("nof_masters", str(self.N_MASTERS), 0)
        self.add_templ("p_entity", self.name, 0)
        # If block has aggregated outputs, close the record definition
        # and add the output record to the entity ports
        if self.out_type is not None:
            self.add_templ("out_record", "end record;\n\n", 2)
            self.add_templ(
                "signal_ports", self.out_name + " : out " + self.out_type + ";\n", 4
            )
        if self.in_type is not None:
            self.add_templ("in_record", "end record;\n\n", 2)
            self.add_templ(
                "signal_ports", self.in_name + " : in " + self.in_type + ";\n", 4
            )
        # The ack_regs port is added only if at least one ack signal was created
        if (self.ack_type is not None) and self.gen_ack :
            self.add_templ("ack_record", "end record;\n\n", 2)
            self.add_templ(
                "signal_ports", self.ack_name + " : out " + self.ack_type + ";\n", 4
            )
        else:
            # We need to clear the start of the record from the template
            self.set_templ("ack_record","")
        # All template is filled, so we can now generate the files
        wb_vhdl_pkg_file = GLB.VHDL_PATH + "/" + self.name + "_pkg.vhd"
        with open(wb_vhdl_pkg_file, "w") as f_o:
            f_o.write(TEMPL_PKG.format(**self.templ_dict))
            created_files["vhdl"].append(wb_vhdl_pkg_file)
        wb_vhdl_file = GLB.VHDL_PATH + "/" + self.name + ".vhd"
        with open(wb_vhdl_file, "w") as f_o:
            f_o.write(templ_wb(self.N_MASTERS).format(**self.templ_dict))
            created_files["vhdl"].append(wb_vhdl_file)

    def amap_xml_hdr(self,ver_hash):
        res = '<module id="' + self.name
        # set is_top depending on the top name
        if self.name == GLB.TOP_NAME:
            res += '" is_top="1'
        res += '" id_hash="0x' + format(self.id_val, "08x")
        res += '" ver_hash="0x' + format(ver_hash, "08x")
        res += '" system_hash="0x' + format(GLB.VER_ID, "08x")
        res += '" addr_bits="' + str(self.adr_bits) + '">\n'
        return res

    def gen_amap_xml(self,nvar=None):
        """ This function generates the address map in the AMAP XML format
            for the nvar variant
        """
        var_id = ""
        if nvar is not None:
            var_id = "_v"+str(nvar)
        hdr = self.amap_xml_hdr(0)
        res = ""
        # Iterate the areas, generating the addresses
        for a_r in self.areas:
            if a_r.obj is None:
                # Registers area
                # Add two standard registers - ID and VER
                adr = a_r.adr
                res += (
                    '  <register id="ID" address="0x'
                    + format(adr+spec_regs["id"], "08x")
                    + '" permission="r"/>\n'
                )
                res += (
                    '  <register id="VER" address="0x'
                    + format(adr + spec_regs["ver"], "08x")
                    + '" permission="r"/>\n'
                )
                if self.testdev_ena != 0:
                    # To enable testing of error detection, all test registers 
                    # have permissions set to "rw"!
                    res += (
                        '  <register id="TEST_RW" address="0x'
                        + format(adr+spec_regs["test_rw"], "08x")
                        + '" permission="rw"/>\n'
                        )
                    res += (
                        '  <register id="TEST_WO" address="0x'
                        + format(adr+spec_regs["test_wo"], "08x")
                        + '" permission="rw"/>\n'
                        )
                    res += (
                        '  <register id="TEST_RO" address="0x'
                        + format(adr+spec_regs["test_ro"], "08x")
                        + '" permission="rw"/>\n'
                        )
                    res += (
                        '  <register id="TEST_TOUT" address="0x'
                        + format(adr+spec_regs["test_tout"], "08x")
                        + '" permission="rw"/>\n'
                        )
                # Now add other registers in a loop
                for reg in self.regs:
                    res += reg.gen_amap_xml(adr,nvar)
            else:
                # Subblock or vector of subblocks
                # If it is a subblock, prefix the name of the table with "agwb_"
                xname = a_r.obj.name
                if isinstance(a_r.obj, WbBlock):
                    xname = "agwb_" + xname + "_amap" + var_id + ".xml"
                if isinstance(a_r.obj, WbBlackBox):
                    if a_r.obj.xmlpath:
                        xname = a_r.obj.xmlpath
                    else:
                        xname = xname + "_amap" + var_id + ".xml"
                if (a_r.var_reps(nvar) == 1) and (a_r.force_vec == False):
                    # Single subblock
                    res += (
                        '  <block id="'
                        + a_r.name
                        + '"'
                        + ' address="0x'
                        + format(a_r.adr, "08x")
                        + '"'
                        + ' module="file://'
                        + xname
                        + '"/>\n'
                    )
                elif (a_r.var_reps(nvar) >= 1):
                    # Not empty vector of subblocks
                    res += (
                        '  <block id="'
                        + a_r.name
                        + '"'
                        + ' address="0x'
                        + format(a_r.adr, "08x")
                        + '" '
                        + ' nelems="'
                        + str(a_r.var_reps(nvar))
                        + '"'
                        + ' elemoffs="0x'
                        + format(a_r.obj.addr_size, "08x")
                        + '"'
                        + ' module="file://'
                        + xname
                        + '"/>\n'
                    )
        res += "</module>\n"
        # Use the generated AMAP XML description as block version ID.
        desc = hdr+res
        blk_ver_id = zlib.crc32(bytes(desc.encode("utf-8")))
        # Now generate a new header with correct hash
        hdr = self.amap_xml_hdr(blk_ver_id)
        desc = hdr+res        
        if nvar is None:
            self.ver_full = blk_ver_id
        else:
            self.ver_var[nvar] =  blk_ver_id
        if GLB.AMAPXML_PATH:
            with open(GLB.AMAPXML_PATH + "/agwb_" + self.name + "_amap" + var_id + ".xml", "w") as f_o:
                f_o.write(desc)

    def gen_ipbus_xml(self):
        """ This function generates the address map in the XML format for ipbus

        """
        res = '<node id="' + self.name + '">\n'
        # Iterate the areas, generating the addresses
        for a_r in self.areas:
            if a_r.obj is None:
                # Registers area
                # Add two standard registers - ID and VER
                adr = a_r.adr
                res += (
                    '  <node id="ID" address="0x'
                    + format(adr+spec_regs["id"], "08x")
                    + '" permission="r"/>\n'
                )
                res += (
                    '  <node id="VER" address="0x'
                    + format(adr + spec_regs["ver"], "08x")
                    + '" permission="r"/>\n'
                )
                if self.testdev_ena != 0:
                    # To enable testing of error detection, all test registers 
                    # have permissions set to "rw"!
                    res += (
                        '  <node id="TEST_RW" address="0x'
                        + format(adr+spec_regs["test_rw"], "08x")
                        + '" permission="rw"/>\n'
                        )
                    res += (
                        '  <node id="TEST_WO" address="0x'
                        + format(adr+spec_regs["test_wo"], "08x")
                        + '" permission="rw"/>\n'
                        )
                    res += (
                        '  <node id="TEST_RO" address="0x'
                        + format(adr+spec_regs["test_ro"], "08x")
                        + '" permission="rw"/>\n'
                        )
                    res += (
                        '  <node id="TEST_TOUT" address="0x'
                        + format(adr+spec_regs["test_tout"], "08x")
                        + '" permission="rw"/>\n'
                        )
                # Now add other registers in a loop
                for reg in self.regs:
                    res += reg.gen_ipbus_xml(adr)
            else:
                # Subblock or vector of subblocks
                # If it is a subblock, prefix the name of the table with "agwb_"
                xname = a_r.obj.name
                if isinstance(a_r.obj, WbBlock):
                    xname = "agwb_" + xname + "_address.xml"
                if isinstance(a_r.obj, WbBlackBox):
                    if a_r.obj.xmlpath:
                        xname = a_r.obj.xmlpath
                    else:
                        xname = xname + "_address.xml"
                if (a_r.reps == 1) and (a_r.force_vec == False):
                    # Single subblock
                    res += (
                        '  <node id="'
                        + a_r.name
                        + '"'
                        + ' address="0x'
                        + format(a_r.adr, "08x")
                        + '"'
                        + ' module="file://'
                        + xname
                        + '"/>\n'
                    )
                else:
                    # Vector of subblocks
                    for n_b in range(0, a_r.reps):
                        res += (
                            '  <node id="'
                            + a_r.name
                            + "["
                            + str(n_b)
                            + ']"'
                            + ' address="0x'
                            + format(a_r.adr + n_b * a_r.obj.addr_size, "08x")
                            + '"'
                            + ' module="file://'
                            + xname
                            + '"/>\n'
                        )
        res += "</node>\n"
        with open(GLB.IPBUS_PATH + "/agwb_" + self.name + "_address.xml", "w") as f_o:
            f_o.write(res)

    def gen_forth(self, parent):
        """ This function generates the address map in the Forth format
            The "path" argument informs how the object should be named in the Forth access words
        """
        # Iterate the areas, generating the addresses
        cdefs = ""
        if self.is_ignored("forth"):
            return cdefs
        for a_r in self.areas:
            if a_r.obj is None:
                # Registers area
                # Add two standard registers - ID and VER
                adr = a_r.adr
                cdefs += (
                    ": " + parent + "_ID " + parent + " $" + format(adr+spec_regs["id"], "x") + " + ;\n"
                )
                cdefs += (
                    ": "
                    + parent
                    + "_VER "
                    + parent
                    + " $"
                    + format(adr + spec_regs["ver"], "x")
                    + " + ;\n"
                )
                if self.testdev_ena != 0:
                    # Add additional test registers (to lower dictionary usage,
                    # the prefix is shortened to _TSTDV)
                   cdefs += (
                        ": " + parent + "_TSTDV_RW " + parent + " $" + format(adr+spec_regs["test_rw"], "x") + " + ;\n"
                   )
                   cdefs += (
                        ": " + parent + "_TSTDV_WO " + parent + " $" + format(adr+spec_regs["test_wo"], "x") + " + ;\n"
                   )
                   cdefs += (
                        ": " + parent + "_TSTDV_RO " + parent + " $" + format(adr+spec_regs["test_ro"], "x") + " + ;\n"
                   )
                   cdefs += (
                        ": " + parent + "_TSTDV_TOUT " + parent + " $" + format(adr+spec_regs["test_tout"], "x") + " + ;\n"
                   )

                # Add two constants
                cdefs += (
                    "$"
                    + format(self.id_val, "x")
                    + " constant "
                    + parent
                    + "_ID_VAL \n"
                )
                cdefs += (
                    "$"
                    + format(self.ver_full, "x")
                    + " constant "
                    + parent
                    + "_VER_VAL \n"
                )
                # Now add other registers in a loop
                for reg in self.regs:
                    cdefs += reg.gen_forth(adr, parent)
            elif not a_r.is_ignored("forth"):
                # Subblock or vector of subblocks
                if (a_r.reps == 1) and (a_r.force_vec == False):
                    node = parent + "_" + a_r.name
                    # Single subblock
                    cdefs += (
                        ": "
                        + node
                        + " "
                        + parent
                        + " $"
                        + format(a_r.adr, "x")
                        + " + ;\n"
                    )
                    cdefs += a_r.obj.gen_forth(node)
                else:
                    # Vector of subblocks
                    node = parent + "#" + a_r.name
                    # Single subblock
                    cdefs += (
                        ": "
                        + node
                        + " "
                        + parent
                        + " $"
                        + format(a_r.adr, "x")
                        + " + swap $"
                        + format(a_r.obj.addr_size, "x")
                        + " * + ;\n"
                    )
                    cdefs += a_r.obj.gen_forth(node)
        return cdefs

    def gen_c_header(self):
        """ This function generates the address map as C/C++ header

        """
        # Each block is responsible for generation of the structure, that fully
        # fills it's address space.
        #
        log.debug("Creating C header:" + self.name + "\n")
        head = "#ifndef __" + self.name + "__INC_H\n"
        head += "#define __" + self.name + "__INC_H\n"
        # Generate the constants with block ID and with version ID
        head += (
            "const uint32_t agwb_" + self.name + "_ID_VAL = " + hex(self.id_val) + ";\n"
        )
        head += (
            "const uint32_t agwb_" + self.name + "_VER_VAL = " + hex(GLB.VER_ID) + ";\n"
        )
        # Iterate the areas, generating the addresses
        # We have to add fillers to ensure proper address allocation
        filler_nr = 1
        cur_addr = 0
        res = "typedef struct {\n"
        # The areas must be sorted by increasing address
        self.areas.sort(key=WbArea.sort_adr)
        for a_r in self.areas:
            # Check if it was nessary to add a filler
            log.debug(a_r.name, a_r.adr, cur_addr)
            if a_r.adr < cur_addr:
                # That should never happen! It would mean that blocks are not ordered properly
                raise Exception("Incorrect ordering of blocks!")
            if a_r.adr > cur_addr:
                res += (
                    "  "
                    + XVOLATILE
                    + " uint32_t filler"
                    + str(filler_nr)
                    + "["
                    + str(a_r.adr - cur_addr)
                    + "];\n"
                )
                filler_nr += 1
                cur_addr = a_r.adr
            if a_r.obj is None:
                # Registers area
                # Add two standard registers - ID and VER
                adr = a_r.adr
                res += "  " + XVOLATILE + " uint32_t ID;\n"
                res += "  " + XVOLATILE + " uint32_t VER;\n"
                cur_addr += 2
                # Conditionally generate the registers for test device.
                # Please note, that the addresses of those registers are not taken from
                # spec_regs array. The structure must be adjusted by hand!
                if self.testdev_ena != 0:
                    # First two registers are not accessible
                    res += "  " + XVOLATILE + " uint32_t TEST_ERR0;\n"
                    res += "  " + XVOLATILE + " uint32_t TEST_ERR1;\n"                    
                    res += "  " + XVOLATILE + " uint32_t TEST_RW;\n"
                    res += "  " + XVOLATILE + " uint32_t TEST_WO;\n"
                    res += "  " + XVOLATILE + " uint32_t TEST_RO;\n"
                    res += "  " + XVOLATILE + " uint32_t TEST_TOUT;\n"
                    cur_addr += 6   
                # Now add other registers in a loop
                for reg in self.regs:
                    r_n, h_n = reg.gen_c_header(adr, self.name)
                    head += h_n
                    res += r_n
                    cur_addr += reg.size
            else:
                # Subblock or vector of subblocks
                # Add the related header
                head += "#include <agwb_" + a_r.obj.name + ".h>\n"
                if (a_r.reps == 1) and (a_r.force_vec == False):
                    # Single subblock
                    res += "  agwb_" + a_r.obj.name + " " + a_r.name + ";\n"
                else:
                    res += (
                        "  agwb_"
                        + a_r.obj.name
                        + " "
                        + a_r.name
                        + "["
                        + str(a_r.reps)
                        + "];\n"
                    )
                cur_addr += a_r.reps * a_r.obj.addr_size
            log.debug(
                "area: "
                + a_r.name
                + " total_size:"
                + str(a_r.total_size)
                + " reps="
                + str(a_r.reps)
                + " cur_adr:"
                + str(cur_addr)
            )
        # Add fillers
        if cur_addr < self.addr_size:
            res += (
                "  "
                + XVOLATILE
                + " uint32_t filler"
                + str(filler_nr)
                + "["
                + str(self.addr_size - cur_addr)
                + "];\n"
            )
            filler_nr += 1
        cur_addr = self.addr_size
        res += "} __attribute__((aligned(4))) agwb_" + self.name + " ;\n"
        res += "#endif\n"
        log.debug("block: " + self.name + " cur_addr=" + str(cur_addr))
        with open(GLB.C_HEADER_PATH + "/agwb_" + self.name + ".h", "w") as f_o:
            f_o.write(head)
            f_o.write(res)

    def gen_python(self,nvar=None):
        """ This function generates the class providing access
        to the block from the Python code"""
        sp4 = 4 * " "
        sp8 = 8 * " "
        res = "\nclass " + self.name + "(agwb.Block):\n"
        res += sp4 + "x__size = " + str(self.addr_size) + "\n"
        res += sp4 + "x__id = " + hex(self.id_val) + "\n"
        if nvar is None:
            res += sp4 + "x__ver = " + hex(self.ver_full) + "\n"
        else:
            res += sp4 + "x__ver = " + hex(self.ver_var[nvar]) + "\n"
        res += sp4 + "x__fields = {\n"
        for a_r in self.areas:
            if a_r.obj is None:
                # Registers area
                # Add two standard register - ID and VER
                adr = a_r.adr
                res += sp8 + "'ID':(" + hex(adr + spec_regs["id"]) + ",(agwb.StatusRegister,)),\\\n"
                res += sp8 + "'VER':(" + hex(adr + spec_regs["ver"]) + ",(agwb.StatusRegister,)),\\\n"
                if self.testdev_ena != 0:
                    # Conditionally add test registers. 
                    # They are added as control registers to enable testing of
                    # read and write addresses.
                    res += sp8 + "'TEST_RW':(" + hex(adr + spec_regs["test_rw"]) + ",(agwb.ControlRegister,)),\\\n"
                    res += sp8 + "'TEST_WO':(" + hex(adr + spec_regs["test_wo"]) + ",(agwb.ControlRegister,)),\\\n"
                    res += sp8 + "'TEST_RO':(" + hex(adr + spec_regs["test_ro"]) + ",(agwb.ControlRegister,)),\\\n"
                    res += sp8 + "'TEST_TOUT':(" + hex(adr + spec_regs["test_tout"]) + ",(agwb.ControlRegister,)),\\\n"                    
                for reg in self.regs:
                    res += reg.gen_python(adr,nvar)
            else:
                # The format depends on whether this is a block or vector of blocks
                if (a_r.var_reps(nvar) == 1) and (a_r.force_vec == False):
                    # Single subblock
                    res += (
                        sp8
                        + "'"
                        + a_r.name
                        + "':("
                        + hex(a_r.adr)
                        + ",("
                        + a_r.obj.name
                        + ",)),\\\n"
                    )
                elif (a_r.var_reps(nvar) >= 1):
                    # Vector of subblocks
                    res += (
                        sp8
                        + "'"
                        + a_r.name
                        + "':("
                        + hex(a_r.adr)
                        + ","
                        + str(a_r.var_reps(nvar))
                        + ",("
                        + a_r.obj.name
                        + ",)),\\\n"
                    )
        res += sp4 + "}\n\n"
        return res

    def gen_html(self, base, mname):
        """ This function generates the description of the particular block in a HTML format """
        res = ""
        # First write the name and description
        res += (
            "<p><b>Address:</b> "
            + hex(base)
            + "-"
            + hex(base + self.addr_size - 1)
            + "<br>"
        )
        res += "<b>Type: </b> " + self.name + "<br>"
        res += "<b>Name: </b> " + mname + "<br>"
        res += "<b>Description:</b>" + self.desc + "</p>"
        # Now generate the collapsible list of address areas
        res += "<details><summary>Areas"
        res += "</summary>"
        res += "<ul>"
        # The areas must be sorted by increasing address
        self.areas.sort(key=WbArea.sort_adr)
        for (
            a_r
        ) in self.areas:  # We assume that they are sorted by increasing base address
            if a_r.obj is None:
                area_name = "Registers"
            else:
                area_name = a_r.name
            res += "<li><details><summary>"
            res += (
                hex(base + a_r.adr)
                + "-"
                + hex(base + a_r.adr + a_r.total_size - 1)
                + " "
                + area_name
            )
            res += "</summary>"
            # Here we generate the detailed description of the area
            if a_r.obj is None:
                # Registers
                res += (
                    hex(base + a_r.adr)
                    + ": "
                    + mname
                    + ".ID = "
                    + hex(self.id_val)
                    + " - block ID register  <br>"
                )
                res += (
                    hex(base + a_r.adr + 1)
                    + ": "
                    + mname
                    + ".VER = "
                    + hex(GLB.VER_ID)
                    + " - block VER register <br>"
                )
                for reg in self.regs:
                    res += reg.gen_html(base + a_r.adr, mname)
            else:
                # Blocks or vectors of blocks
                if (a_r.reps == 1) and (a_r.force_vec == False):
                    # Single block
                    res += a_r.obj.gen_html(base + a_r.adr, mname + "." + a_r.name)
                else:
                    # Vector of blocks
                    for i in range(0, a_r.reps):
                        res += a_r.obj.gen_html(
                            base + a_r.adr + i * a_r.obj.addr_size,
                            mname + "." + a_r.name + "[" + str(i) + "]",
                        )
            res += "</details></li>"
        res += "</ul>"
        res += "</details>"
        return res
