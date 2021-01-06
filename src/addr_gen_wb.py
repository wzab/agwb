#!/usr/bin/python3
"""
This is the script that generates the VHDL code needed to access
the registers in a hierarchical Wishbone-conencted system.

Written by Wojciech M. Zabolotny
(wzab01<at>gmail.com or wzab<at>ise.pw.edu.pl)

Significant improvements by
Michal Kruszewski (mkru<at>protonmail.com)
and
Marek Guminski (marek.guminski<at>gmail.com)

The code is published under LGPL V2 license
"""
from lxml import etree
import xml.etree.ElementTree as et
import xml.parsers.expat as pe
from io import StringIO
import os
import sys
import shutil
import zlib
import argparse
import wb_block as wb
import include

# The module expressions accepts definitions of constants (function addval)
# and evaluates the expressions (function exprval)
import expressions as ex
import yaml


PARSER = argparse.ArgumentParser()
PARSER.add_argument("--infile", help="Input file path", default="../example1.xml")
PARSER.add_argument("--hdl", help="VHDL outputs destination", default="")
PARSER.add_argument("--ipbus", help="IPbus outputs destination", default="")
PARSER.add_argument("--amapxml", help="AMap XML outputs destination", default="")
PARSER.add_argument("--header", help="C header outputs destination", default="")
PARSER.add_argument("--fs", help="Forth outputs destination", default="")
PARSER.add_argument("--python", help="Python outputs destination", default="")
PARSER.add_argument("--html", help="HTML documentation destination", default="")
PARSER.add_argument(
    "--fusesoc", help="Generate FuseSoc .core file", action="store_true"
)
PARSER.add_argument("--fusesoc_vlnv", help="FuseSoc VLNV tag", default="")
ARGS = PARSER.parse_args()

INFILENAME = ARGS.infile

wb.GLB.IPBUS_PATH = ARGS.ipbus
if wb.GLB.IPBUS_PATH:
    os.makedirs(wb.GLB.IPBUS_PATH, exist_ok=True)

wb.GLB.AMAPXML_PATH = ARGS.amapxml
if wb.GLB.AMAPXML_PATH:
    os.makedirs(wb.GLB.AMAPXML_PATH, exist_ok=True)

wb.GLB.VHDL_PATH = ARGS.hdl
if wb.GLB.VHDL_PATH:
    os.makedirs(wb.GLB.VHDL_PATH, exist_ok=True)

wb.GLB.FORTH_PATH = ARGS.fs
if wb.GLB.FORTH_PATH:
    os.makedirs(wb.GLB.FORTH_PATH, exist_ok=True)

wb.GLB.C_HEADER_PATH = ARGS.header
if wb.GLB.C_HEADER_PATH:
    os.makedirs(wb.GLB.C_HEADER_PATH, exist_ok=True)

wb.GLB.PYTHON_PATH = ARGS.python
if wb.GLB.PYTHON_PATH:
    os.makedirs(wb.GLB.PYTHON_PATH, exist_ok=True)

wb.GLB.HTML_PATH = ARGS.html
if wb.GLB.HTML_PATH:
    os.makedirs(wb.GLB.HTML_PATH, exist_ok=True)

# The line below reads the XML and recursively inserts included XMLs
# it also generates the list of objects describing the origin of each line
# in the final XML (to facilitate future error detection)
FINAL_XML, LINES_ORIGIN = include.handle_includes(INFILENAME)

# The version ID is calculated as a hash of the XML defining the interface
# it is encoded in UTF-8, to avoid problems with different locales
wb.GLB.VER_ID = zlib.crc32(bytes(FINAL_XML.encode("utf-8")))

# We get the root element, and find the corresponding block
try:
    EL_ROOT = et.fromstring(FINAL_XML)
except et.ParseError as perr:
    # Handle the parsing error
    ROW, COL = perr.position
    print(
        "Parsing error "
        + str(perr.code)
        + "("
        + pe.ErrorString(perr.code)
        + ") in column "
        + str(COL)
        + " of the line "
        + str(ROW)
        + " of the concatenated XML:"
    )
    print(FINAL_XML.split("\n")[ROW - 1])
    print(COL * "-" + "|")
    print("The erroneous line was produced from the following sources:")
    ERR_SRC = include.find_error(LINES_ORIGIN, ROW)
    for src in ERR_SRC:
        print("file: " + src[0] + ", line:" + str(src[1]))
    sys.exit(1)

# Check tree with RELAX NG schema
lxml_parser = etree.XMLParser(dtd_validation=True)
relax_ng_path = os.path.join(os.path.dirname(__file__), "relax_ng.xml")
relaxng_doc = etree.parse(relax_ng_path)
relax_ng = etree.RelaxNG(relaxng_doc)
agwb_tree = etree.parse(StringIO(FINAL_XML))
valid = relax_ng.validate(agwb_tree)
if not valid:
    raise Exception(relax_ng.error_log)

TOP_NAME = EL_ROOT.attrib["top"]
if "masters" in EL_ROOT.attrib:
    N_MASTERS = ex.exprval(EL_ROOT.attrib["masters"])
else:
    N_MASTERS = 1
# Find constants and feed them into the expressions module
for el in EL_ROOT.findall("constant"):
    ex.addval(el.attrib["name"], el.attrib["val"])
# We prepare the packages with constants for different backends
# For VHDL
if wb.GLB.VHDL_PATH:
    with open(wb.GLB.VHDL_PATH + "/agwb_pkg.vhd", "w") as fo:
        fo.write(
"""--- This file has been automatically generated
--- by the agwb (https://github.com/wzab/agwb).
--- Please don't edit it manually, unless you really have to do it
library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;

library general_cores;
use general_cores.wishbone_pkg.all;

package agwb_pkg is


  constant c_WB_SLAVE_OUT_ERR : t_wishbone_slave_out :=
    (ack => '0', err => '1', rty => '0', stall => '0', dat => c_DUMMY_WB_DATA);

  type t_reps_variants is array (integer range <>) of integer;
  type t_ver_id_variants is array (integer range <>) of std_logic_vector(31 downto 0);

end package agwb_pkg;
"""
        )        
    with open(wb.GLB.VHDL_PATH + "/" + TOP_NAME + "_const_pkg.vhd", "w") as fo:
        fo.write(
            """library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;
library work;
"""
        )
        fo.write("package " + TOP_NAME + "_const_pkg is\n")
        fo.write(
                "constant C_" + TOP_NAME + "_system_ver"
                + " : std_logic_vector(31 downto 0) := "
                + 'x"' + format(wb.GLB.VER_ID, "08x") + '";\n'
            )
        for cnst in ex.defines:
            fo.write(
                "constant C_"
                + cnst
                + " : integer := "
                + str(ex.defines[cnst])
                + "; -- "
                + ex.comments[cnst]
                + "\n"
            )
        fo.write("end package;\n")
# For C
if wb.GLB.C_HEADER_PATH:
    with open(wb.GLB.C_HEADER_PATH + "/agwb_" + TOP_NAME + "_const.h", "w") as fo:
        GUARD_NAME = "_agwb_" + TOP_NAME + "_inc_H_"
        fo.write("#ifndef " + GUARD_NAME + "\n")
        fo.write("#define " + GUARD_NAME + "\n\n")
        for cnst in ex.defines:
            fo.write(
                "#define "
                + cnst
                + " "
                + str(ex.defines[cnst])
                + " // "
                + ex.comments[cnst]
                + "\n"
            )
        fo.write("\n#endif\n")
# For Python
if wb.GLB.PYTHON_PATH:
    dst_path = wb.GLB.PYTHON_PATH + "/agwb"
    os.makedirs(dst_path, exist_ok=True)
    src_path = os.path.join(os.path.dirname(__file__), "../targets/python/agwb/")
    shutil.copy(src_path + "__init__.py", dst_path)
    shutil.copy(src_path + "agwb.py", dst_path)
    with open(wb.GLB.PYTHON_PATH + "/agwb/" + TOP_NAME + "_const.py", "w") as fo:
        for cnst in ex.defines:
            fo.write(
                cnst + " = " + str(ex.defines[cnst]) + " # " + ex.comments[cnst] + "\n"
            )
    with open(wb.GLB.PYTHON_PATH + "/agwb/" + "__init__.py", "a") as f:
        f.write(
                "from ." + TOP_NAME + "_const import *\n"
        )
# Generation of constants for Forth is added to the generation of
# the access words

# Now we find the top block definition

# We should evaluate the address space requirements in each block
# In the first run, we calculate the space occupied by registers,
# but as blocks may be defined in different order, we also
# analyze the block dependencies.

# Create the list of blocks
for el in EL_ROOT.findall("block"):
    # Here we take each block and count registers inside
    # We also prepare the list of subblocks (of vectors of
    # subblocks)
    bn = el.attrib["name"]
    if bn in wb.blocks():
        raise Exception("Duplicate definition of block: " + bn)
    bl = wb.WbBlock(el)
    wb.blocks()[bn] = bl
# Here we have everything, we could get from the first scan.
BL = wb.blocks()[TOP_NAME]
# overwite the number of master ports in the top module
BL.N_MASTERS = N_MASTERS
BL.analyze()

# Create the list of variants for formats that support it
variants = [None,]
if wb.GLB.variants > 1:
    variants += range(0,wb.GLB.variants)

# Now we generate the AMAPXML address tables for possible variants
# This target must be run first, as it generates VER ID for blocks
# The blobk gen_amap_xml checks if the output path exists.
for nvar in variants:
    for key, BL in wb.blocks().items():
        if BL.used:
            BL.gen_amap_xml(nvar)

# Now we can generate the VHDL code that implements
# the system
if wb.GLB.VHDL_PATH:
    for key, BL in wb.blocks().items():
        if BL.used:
            BL.gen_vhdl()
# Now we generate the Python access code
if wb.GLB.PYTHON_PATH:
    res = """\"\"\"
This file has been automatically generated
by the agwb (https://github.com/wzab/agwb).
Do not modify it by hand.
\"\"\"\n
"""
    res += "from . import agwb\n\n"
    for key, BL in wb.blackboxes().items():
        res += BL.gen_python()
    for key, BL in wb.blocks().items():
        if BL.used:
            res += BL.gen_python()
    with open(wb.GLB.PYTHON_PATH + "/agwb/" + TOP_NAME + ".py", "w") as fo:
        fo.write(res)
    with open(wb.GLB.PYTHON_PATH + "/agwb/" + "__init__.py", "a") as f:
        f.write(
                "from ." + TOP_NAME + " import *\n"
        )
        
# Now we generate the IPbus address tables
if wb.GLB.IPBUS_PATH:
    for key, BL in wb.blocks().items():
        if BL.used:
            BL.gen_ipbus_xml()

# Now we generate the C address tables
if wb.GLB.C_HEADER_PATH:
    for key, BL in wb.blackboxes().items():
        BL.gen_c_header()
    for key, BL in wb.blocks().items():
        if BL.used:
            BL.gen_c_header()
# Generate the Forth address table
BL = wb.blocks()[TOP_NAME]
if wb.GLB.FORTH_PATH:
    with open(wb.GLB.FORTH_PATH + "/agwb_" + TOP_NAME + ".fs", "w") as fo:
        # First generate constants
        for cnst in ex.defines:
            fo.write(
                ": /%"
                + cnst
                + " $"
                + format(ex.defines[cnst], "x")
                + " ; \\ "
                + ex.comments[cnst]
                + "\n"
            )
        # Now generate the HW access words
        ROOT_WORD = "//"
        # Add empty definition for ROOT_WORD
        fo.write(": " + ROOT_WORD + " $0 ;\n")
        fo.write(BL.gen_forth(ROOT_WORD))

if wb.GLB.HTML_PATH:
    with open(wb.GLB.HTML_PATH + "/agwb_address_map.html", "w") as fo:
        fo.write(BL.gen_html(0, ""))

if ARGS.fusesoc:
    with open("./agwb_" + TOP_NAME + ".core", "w") as fo:
        fo.write("CAPI=2:\n")

        coredata = {
            "name": ARGS.fusesoc_vlnv,
            "targets": {"default": {}},
        }

        created_files = wb.created_files["vhdl"]
        created_files.insert(0,wb.GLB.VHDL_PATH + "/agwb_pkg.vhd")
        created_files.append(wb.GLB.VHDL_PATH + "/" + TOP_NAME + "_const_pkg.vhd")
        coredata["filesets"] = {
            "rtl": {
                "files": created_files,
                "file_type": "vhdlSource-93",
                "logical_name": "agwb",
            }
        }
        coredata["targets"]["default"]["filesets"] = ["rtl"]

        fo.write(yaml.dump(coredata))
