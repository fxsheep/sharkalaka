#!/usr/bin/env python3

import usb.core, binascii

SPRD_EP_IN = 0x85
SPRD_EP_OUT = 0x6
SPRD_XFER_MAX_LEN = 1024
SPRD_DEFAULT_TIMEOUT = 200

BSL_CMD_CONNECT = 0x0
BSL_CMD_START_DATA = 0x1
BSL_CMD_MIDST_DATA = 0x2
BSL_CMD_END_DATA = 0x3
BSL_CMD_EXEC_DATA = 0x4

BSL_REP_ACK = 0x80
BSL_REP_VER = 0x81

def calc_crc16(data, crc=0):
    return binascii.crc_hqx(data, crc)

def translate(data):
    transdata = bytes([0x7E])
    for char in data:
        if(char == 0x7E):
            transdata += bytes([0x7D, 0x5E])
        elif(char == 0x7D):
            transdata += bytes([0x7D, 0x5D])
        else:
            transdata += bytes([char])
    transdata += bytes([0x7E])
    return transdata

def detranslate(data):
    lst = list(data)
    if(lst[0] != 0x7E or lst[-1] != 0x7E):
        print("Error: Malformed packet received.")
        return
    del lst[0]
    del lst[-1]
    i = 0
    detransdata = b''
    while(i <= (len(lst) - 1)):
        if(lst[i] == 0x7D and lst[i+1] == 0x5E):
            detransdata += bytes([0x7E])
            i += 2
        elif(lst[i] == 0x7D and lst[i+1] == 0x5D):
            detransdata += bytes([0x7D])
            i += 2
        else:
            detransdata += bytes([lst[i]])
            i += 1
    return detransdata

def generate_packet(command, data=b''):
    packet = command.to_bytes(2, byteorder="big", signed=False)
    packet += len(data).to_bytes(2, byteorder="big", signed=False)
    if(len(data)):
        packet += data
    packet += calc_crc16(packet).to_bytes(2, byteorder="big", signed=False)
    return translate(packet)

def parse_packet(packet):
    packet = detranslate(packet)
    if(packet == None):
        print("Error: Packet parse failed.")
        return
    command = int.from_bytes(packet[0:2],byteorder='big',signed=False)
    length = int.from_bytes(packet[2:4],byteorder='big',signed=False)
    data = packet[4:-2]
    if(length != len(data)):
        print("Error: Packet length incorrect.")
        return
    crc = int.from_bytes(packet[-2:],byteorder='big',signed=False)
    if(calc_crc16(packet[:-2]) != crc):
        print("Warning: CRC16 error detected!")
    else:
        crc_match = 1
    return command, data, crc_match

class SprdFlasher():

    def __init__(self):
        self.usbdevice = None
        self.timeout = SPRD_DEFAULT_TIMEOUT

    def acquire_device(self):
        dev = usb.core.find(idVendor=0x1782, idProduct=0x4d00)
        if(dev):
            dev.set_configuration()
            self.usbdevice = dev
            return True
        else:
            return False

    def send_data(self, data, timeout=None):
        if(timeout == None):
            timeout = self.timeout
        self.usbdevice.write(SPRD_EP_OUT, data, timeout)

    def read_data(self, max_length=SPRD_XFER_MAX_LEN, timeout=None):
        if(timeout == None):
            timeout = self.timeout
        return bytes(self.usbdevice.read(SPRD_EP_IN, max_length, timeout))

    def send_ping(self):
        self.send_data(b'\x7E')

    def send_connect(self):
        self.send_data(generate_packet(BSL_CMD_CONNECT))

    def send_start(self, addr, total_size):
        data = addr.to_bytes(4, byteorder="big", signed=False)
        data += total_size.to_bytes(4, byteorder="big", signed=False)
        self.send_data(generate_packet(BSL_CMD_START_DATA, data))

    def send_midst(self, data):
        self.send_data(generate_packet(BSL_CMD_MIDST_DATA, data))

    def send_end(self):
        self.send_data(generate_packet(BSL_CMD_END_DATA))

    def send_exec(self):
        self.send_data(generate_packet(BSL_CMD_EXEC_DATA))
    
    def read_packet(self):
        return parse_packet(self.read_data())

    def read_version(self):
        response, data, crc_match = self.read_packet()
        if(response != BSL_REP_VER):
            print("Error: Invalid version response.")
            return
        return data.decode('utf-8','ignore')

    def read_ack(self):
        response, data, crc_match = self.read_packet()
        if(response != BSL_REP_ACK or len(data)):
            print("Error: Invalid ACK received.")
            return False
        return True
