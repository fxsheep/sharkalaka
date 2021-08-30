#!/usr/bin/env python3

import sprdflasher, binascii, os, sys, time

MIDST_SIZE = 528

flasher = sprdflasher.SprdFlasher()

if(flasher.acquire_device() == False):
    print("No device found.")
    quit()

flasher.send_ping()
print("BootROM version:", flasher.read_version())
flasher.send_connect()
assert flasher.read_ack()

file = sys.argv[2]
addr = int(sys.argv[1], base=16)
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
print("Download finished, executing loader...")
flasher.send_exec()
assert flasher.read_ack()

flasher.set_chksum_type("add")

for i in range(0, 10):
    flasher.send_ping()
    ver = flasher.read_version()
    if(ver):
        break
print("FDL1 version:", ver)

flasher.send_connect()
assert flasher.read_ack()

file = sys.argv[4]
addr = int(sys.argv[3], base=16)
f = open(file, "rb")
remain_size = size = os.stat(file).st_size

print("Downloading U-Boot to",hex(addr))
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
print("Download finished, executing downloader...")
flasher.send_exec()

for i in range(0,10):
    response, data, chksum_match = flasher.read_packet()
    if(response):
        break

if(response == 0x96):
    print("U-Boot/FDL2 is up and running!")
else:
    print("U-Boot/FDL2 is not alive!")

