STD=standard
#STD=synopsys
VSTD=93c
ENTITY=wb_test_top_tb
# --unbuffered option must be added in the new GHDL
RUN_OPTIONS= --unbuffered --stop-time=5000ns --wave=${ENTITY}.ghw 
#RUN_OPTIONS+= --trace-signals
#RUN_OPTIONS= --stop-time=290000ns 
#RUN_OPTIONS=  --wave=${ENTITY}.ghw 
SOURCES_GC = \
 general-cores/modules/genrams/genram_pkg.vhd \
 general-cores/modules/wishbone/wishbone_pkg.vhd \
 general-cores/modules/wishbone/wb_crossbar/xwb_crossbar.vhd \

SOURCES_AGWB = \
 ../../hdl/agwb_pkg.vhd \
 gen/MAIN_const_pkg.vhd \
 gen/SYS1_pkg.vhd \
 gen/SYS1.vhd \
 gen/MAIN_pkg.vhd \
 gen/MAIN.vhd \

SOURCES = \
 hdl/sys1.vhd \
 hdl/htest.vhd \
 hdl/exttest.vhd \
 hdl/wb_cdc.vhd \
 hdl/main.vhd \
 hdl/sim_wb_ctrl.vhd \
 hdl/wb_test_top.vhd \
 hdl/wb_test_top_tb.vhd \

OBJECTS=$(SOURCES:.vhd=.o)
OBJECTS_GC=$(SOURCES_GC:.vhd=.o)
OBJECTS_AGWB=$(SOURCES_AGWB:.vhd=.o)

all: show

$(OBJECTS): %.o : %.vhd
	ghdl -a -g -C  --std=${VSTD} --ieee=${STD} $<
$(OBJECTS_AGWB): %.o : %.vhd
	ghdl -a -g --work=agwb -C  --std=${VSTD} --ieee=${STD} $<
$(OBJECTS_GC): %.o : %.vhd
	ghdl -a -g --work=general_cores -C  --std=${VSTD} --ieee=${STD} $<
#	ghdl -a -g -C --workdir=comp --std=${VSTD} --ieee=${STD} $<

#--trace-signals --trace-processes
#RUN_OPTIONS= 
#--trace-processes
show:   ${ENTITY} ${ENTITY}.ghw
	gtkwave ${ENTITY}.ghw ${ENTITY}.sav
${ENTITY}: ${OBJECTS_GC} ${OBJECTS_AGWB} ${OBJECTS}
#	vhdlp -work fmf fmf/*.vhd
#	ghdl -e -g --mb-comments --workdir=comp --std=${VSTD} -fexplicit --ieee=${STD} ${ENTITY}
	ghdl -e -g --mb-comments  --std=${VSTD} -fexplicit --ieee=${STD} ${ENTITY}
${ENTITY}.ghw: ${ENTITY}
#	./${ENTITY} --wave=${ENTITY}.ghw  ${RUN_OPTIONS} --stop-time=50000ns 2>&1 > res.txt
	./${ENTITY} ${RUN_OPTIONS} 
#> res.txt  2>&1 
clean:
	rm -f comp/* *.o *.vcd *.ghw *.cf events* ${ENTITY}

