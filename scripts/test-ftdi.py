#!/usr/bin/env python3

from time import sleep
from pyftdi.ftdi import Ftdi

#print(Ftdi.show_devices())

f1 = Ftdi.create_from_url('ftdi://ftdi:232:FTGSQ36H/1')

while True:
    f1.set_rts(True);
    sleep(2)
    f1.set_rts(False);
    sleep(2);
