#! /usr/bin/python3
#
# Copyright (c) 2018 Warren J. Jasper <wjasper@ncsu.edu>
#
# This library is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation; either
# version 2.1 of the License, or (at your option) any later version.
#
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
# Lesser General Public License for more details.
# You should have received a copy of the GNU Lesser General Public
# License along with this library; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA

import socket
import sys

# Global constants
DISCOVER_PORT =   54211
COMMAND_PORT =    54211
SCAN_PORT =       54212
    
MSG_SUCCESS =         0 # Command succeeded
MSG_ERROR_PROTOCOL =  1 # Command failed due to improper protocol (number of expected data bytes did not match protocol definition)
MSG_ERROR_PARAMETER = 2 # Command failed due to invalid parameters (the data contents were incorrect)
MSG_ERROR_BUSY =      3 # Command failed because the resource was busy
MSG_ERROR_READY =     4 # Command failed because the resource was not ready
MSG_ERROR_TIMEOUT =   5 # Command failed due to a resource timeout
MSG_ERROR_OTHER =     6 # Command failed due to some other error

MSG_HEADER_SIZE =     6
MSG_CHECKSUM_SIZE =   1

MSG_INDEX_START =      0
MSG_INDEX_COMMAND =    1
MSG_INDEX_FRAME =      2
MSG_INDEX_STATUS =     3
MSG_INDEX_COUNT_LOW =  4  # The maximum value for count is 1024
MSG_INDEX_COUNT_HIGH = 5
MSG_INDEX_DATA =       6

MSG_REPLY =            0x80
MSG_START =            0xDB


class mccEthernetDevice:

  def __init__(self, productID=None, device_address=None):
    self.nfound = 0                                          # number of devices found
    self.commandPort = 54211
    
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)     # create the socket
    s.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)  # set the broadcast option
    s.settimeout(1.0)                                        # set noblocking 1 second timeout
    s.bind(('', DISCOVER_PORT))                              # bind the socket for receive
    msg = 'D'
    #send a broadcast discover datagram
    s.sendto(msg.encode(), ('<broadcast>', DISCOVER_PORT)) 
    while True:
      try:
        msg, address = s.recvfrom(1024)
        if (len(msg) == 64):
          self.address = address[0]
          self.MAC = 0x0
          for i in range(1,7):
            self.MAC += (msg[i]<<((6-i)*8))
          self.NetBIOS = msg[11:26].decode()
          self.productID = msg[7] + (msg[8]<<8)
          self.firmwareVersion = msg[9] + (msg[10]<<8)
          self.bootloadVersion = msg[39] +( msg[40]<<8)
          if (self.productID == productID):
            self.nfound += 1
            self.frameID = 0
            self.connectCode = 0x0
      except:
        s.close()
        return 

  def printDeviceInfo(self):
    print('Number devices found =', self.nfound)
    print('  Found device: ', self.NetBIOS)
    print('  IP address:', self.address)
    print('  Product ID:', hex(self.productID))
    print('  Command Port:', self.commandPort)
    print('  MAC:', hex(self.MAC>>40&0xff)[2:].zfill(2)+':'+\
          hex(self.MAC>>32&0xff)[2:]+':'+\
          hex(self.MAC>>24&0xff)[2:]+':'+\
          hex(self.MAC>>16&0xff)[2:]+':'+\
          hex(self.MAC>>8&0xff)[2:]+':'+\
          hex(self.MAC&0xff)[2:])
    print('  Boot version:', str(self.bootloadVersion>>8)+'.'+str(self.bootloadVersion&0xff))
    print('  Firmware version:', str(self.firmwareVersion>>8)+'.'+str(self.firmwareVersion&0xff))

  def mccOpenDevice(self, connectCode):
    # open the UDP socket
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)     # create the socket
    try:
      s.connect((self.address, DISCOVER_PORT))
    except:
      raise
    # send the connect message
    msg = bytearray(5)
    msg[0] = ord('C')
    msg[1] = connectCode>>24&0xff
    msg[2] = connectCode>>16&0xff
    msg[3] = connectCode>>8&0xff
    msg[4] = connectCode&0xff

    s.settimeout(1)          # set noblocking 1 second timeout
    s.send(msg)
    try:
      data = s.recv(10)
    except socket.timeout:
      raise
      print('mccOpenDevice: timeout error.\n')
      s.close()
      return
    s.close()
    if (len(data) == 2 and chr(data[0]) == 'C' and bytes(data)[1] == 0x0):
      # connection made
      pass
    elif bytes(data)[1] == 0x1:
      print('mccOpenDevice: Incorrect connect code.\n')
      return
    elif bytes(data)[1] == 0x2:
      print('mccOpenDevice: conntion ignored.\n')
      return
    elif bytes(data)[1] == 0x3:
      print('mccOpenDevice: device in use.\n')
      return
    else:
      print('mccOpenDevice: unknown value.\n')
      return
    
    # finished with the UDP portion.

    # create connection with TCP socket
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect((self.address, COMMAND_PORT))
    self.sock = s
    return s

  def calcChecksum(self, buf, length):
    checksum = 0
    for i in range(length):
      checksum += buf[i]
    return (checksum & 0xff)
