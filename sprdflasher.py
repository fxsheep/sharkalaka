#!/usr/bin/env python3

import usb.core, binascii

SPRD_EP_IN = 0x85
SPRD_EP_OUT = 0x6
SPRD_XFER_MAX_LEN = 1024
SPRD_DEFAULT_TIMEOUT = 200

CHKSUM_TYPE_CRC16 = 1
CHKSUM_TYPE_ADD = 2

BSL_CMD_CONNECT = 0x0
BSL_CMD_START_DATA = 0x1
BSL_CMD_MIDST_DATA = 0x2
BSL_CMD_END_DATA = 0x3
BSL_CMD_EXEC_DATA = 0x4

BSL_REP_ACK = 0x80
BSL_REP_VER = 0x81

chksum_type = 0

def calc_chksum(data):
    if(chksum_type == CHKSUM_TYPE_CRC16):
        return binascii.crc_hqx(data, 0)
    elif(chksum_type == CHKSUM_TYPE_ADD):
        sum = 0
        size = i = len(data)
        while(i > 1):
            sum += (data[size - i] + (data[size - i + 1] << 8))
            i -= 2
        if(i == 1):
            sum = sum + data[size - i]
        sum = (sum >> 16) + (sum & 0xFFFF)
        sum += (sum >> 16)
        sum = (~sum) & 0xFFFF
        sum = ((sum >> 8) | (sum << 8)) & 0xFFFF
        return sum
    else:
        print("Error: Checksum type is incorrect.")
        return

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
    packet += calc_chksum(packet).to_bytes(2, byteorder="big", signed=False)
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
    chksum = int.from_bytes(packet[-2:],byteorder='big',signed=False)
    if(calc_chksum(packet[:-2]) != chksum):
        print("Warning: Checksum error detected.")
        chksum_match = 0
    else:
        chksum_match = 1
    return command, data, chksum_match

class SprdFlasher():

    def __init__(self):
        self.usbdevice = None
        self.timeout = SPRD_DEFAULT_TIMEOUT
        self.set_chksum_type("crc16")

    def set_chksum_type(self, type):
        global chksum_type
        if(type == "crc16"):
            chksum_type = CHKSUM_TYPE_CRC16
        elif(type == "add"):
            chksum_type = CHKSUM_TYPE_ADD
        else:
            print("Checksum type incorrect.")

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
        try:
            self.usbdevice.write(SPRD_EP_OUT, data, timeout)
            return True
        except usb.core.USBTimeoutError:
            return False

    def read_data(self, max_length=SPRD_XFER_MAX_LEN, timeout=None):
        if(timeout == None):
            timeout = self.timeout
        try:
            return bytes(self.usbdevice.read(SPRD_EP_IN, max_length, timeout))
        except usb.core.USBTimeoutError:
            return None

    def send_ping(self):
        return self.send_data(b'\x7E')

    def send_connect(self):
        return self.send_data(generate_packet(BSL_CMD_CONNECT))

    def send_start(self, addr, total_size):
        data = addr.to_bytes(4, byteorder="big", signed=False)
        data += total_size.to_bytes(4, byteorder="big", signed=False)
        return self.send_data(generate_packet(BSL_CMD_START_DATA, data))

    def send_midst(self, data):
        return self.send_data(generate_packet(BSL_CMD_MIDST_DATA, data))

    def send_end(self):
        return self.send_data(generate_packet(BSL_CMD_END_DATA))

    def send_exec(self):
        return self.send_data(generate_packet(BSL_CMD_EXEC_DATA))
    
    def read_packet(self):
        try:
            return parse_packet(self.read_data())
        except:
            return None, None, None

    def read_version(self):
        response, data, chksum_match = self.read_packet()
        if(response != BSL_REP_VER):
            print("Error: Invalid version response.")
            return
        return data.decode('utf-8','ignore')

    def read_ack(self):
        response, data, chksum_match = self.read_packet()
        if(response != BSL_REP_ACK or len(data)):
            print("Error: Invalid ACK received.")
            return False
        return True
