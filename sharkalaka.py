#!/usr/bin/env python3

import sprdflasher, binascii, os

MIDST_SIZE = 528

DOWNLOAD_ADDR = 0x40000000
FDL1_FILENAME = "fdl1.bin"

flasher = sprdflasher.SprdFlasher()

if(flasher.acquire_device() == False):
    print("No device found.")
    quit()
flasher.send_ping()
print("BootROM version:", flasher.read_version())
flasher.send_connect()
assert flasher.read_ack()

file = FDL1_FILENAME
addr = DOWNLOAD_ADDR
f = open(file, "rb")
remain_size = size = os.stat(file).st_size

print("Downloading SRAM loader to",hex(addr))
flasher.send_start(addr,size)
assert flasher.read_ack()

while(remain_size > 0):
    if(remain_size > MIDST_SIZE):
        flasher.send_midst(f.read(MIDST_SIZE))
        assert flasher.read_ack()
        remain_size -= MIDST_SIZE
    else:
        flasher.send_midst(f.read(remain_size))
        assert flasher.read_ack()
        remain_size = 0

f.close()

flasher.send_end()
assert flasher.read_ack()
print("Dwonload finished, executing loader...")
flasher.send_exec()
assert flasher.read_ack()
