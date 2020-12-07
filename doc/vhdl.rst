VHDL
----

AGWB generates VHDL files appropriate to the defined blocks (see :ref:`Output products`).
When AGWB is used as a FuseSoc generator all auto generated VHDL files are put into separate :code:`agwb` library.
If user generates code using script directly (without FuseSoc), the generated files can be put into any library.
However, it is recommended to always put auto generated VHDL files into dedicatd :code:`agwb` library, even if FuseSoc is not used.
This makes the design more readable and facilitates the maintenance.

Conversion functions
####################

In VHDL there is often a need to convert objects to different types.
AGWB automatically generates functions for converting to :code:`std_logic_vector` and custom types defined in .xml files.

**Example**

Assume there is following block defined in the .xml file.

.. code-block:: xml

   <block name="my_block">
      <creg name="my_creg">
         <field name="field_1" width="5"/>
         <field name="field_2" width="3"/>
      </creg>
   </block>

Then following declarations and definitions will be automatically generated and available in the :code:`my_block_pkg.vhd` file.

.. code-block:: vhdl

   type t_my_creg is record
      field_1 : std_logic_vector(4 downto 0);
      field_2 : std_logic_vector(2 downto 0);
   end record;

   function to_my_creg(x : std_logic_vector) return t_my_creg;
   function to_slv(x : t_my_creg) return std_logic_vector;

   -- Definitions from the package body.
   function to_my_creg(x : std_logic_vector) return t_my_creg is
   variable res : t_my_creg;
   begin
      res.field_1 := std_logic_vector(x(4 downto 0));
      res.field_2 := std_logic_vector(x(7 downto 5));
      return res;
   end function;
   
   function to_slv(x : t_sx_mask_enc_mode) return std_logic_vector is
   variable res : std_logic_vector(7 downto 0);
   begin
      res(4 downto 0) := std_logic_vector(x.field_1);
      res(7 downto 5) := std_logic_vector(x.field_2);
      return res;
   end function;
