#!/usr/bin/python3
import cbus
nodes=cbus.cbus_read_nodes('gen','MAIN_address.xml')
cbus.bus_delay(100)
print("Test the ID")
print ("ID read:"+ hex(nodes['ID'].read()))
print ("VER read:"+ hex(nodes['VER'].read()))
cbus.bus_delay(250)
print("LINKS1 ID read:"+hex(nodes['LINKS[0].ID'].read()))
print("LINKS1 VER read:"+hex(nodes['LINKS[0].VER'].read()))
cbus.bus_delay(250)
print("LINKS1 STATUS read:"+hex(nodes['LINKS[0].STATUS'].read()))
cbus.bus_delay(250)
print("LINKS1 CTRL write")
nodes['LINKS[0].CTRL'].write(0xdce432)
cbus.bus_delay(250)
print("LINKS4 STATUS read:"+hex(nodes['LINKS[4].STATUS'].read()))
cbus.bus_delay(250)
print("LINKS4 CTRL write")
nodes['LINKS[4].CTRL'].write(0x35678)
cbus.bus_delay(3000)


