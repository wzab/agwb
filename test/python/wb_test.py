#!/usr/bin/python3
import cbus
cnt=0x0
mem=0x0
mem_mod=0x80000000
cbus.bus_delay(100)
print("Test the counter")
cbus.bus_read(cnt)
cbus.bus_delay(250)
print("First read:"+hex(cbus.bus_read(cnt)))
cbus.bus_delay(250)
print("2nd read:"+hex(cbus.bus_read(cnt)))
cbus.bus_delay(250)
print("3rd read:"+hex(cbus.bus_read(cnt)))
cbus.bus_delay(250)
print("4th read:"+hex(cbus.bus_read(cnt)))
print("\nTest the memory")
for i in range(0,10):
  cbus.bus_write(mem+i,i*2)
cbus.bus_delay(250)
print("Read from memory:")
for i in range(0,10):
  print("mem["+str(i)+"]="+hex(cbus.bus_read(mem+i)))
print("Read from memory modified by adding 12 and the address:")
for i in range(0,10):
  print("mem_mod["+str(i)+"]="+hex(cbus.bus_read(mem_mod+i)))
cbus.bus_delay(3000)


