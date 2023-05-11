# RNode interface class for Python 3
#
# MIT License
#
# Copyright (c) 2020 Mark Qvist - unsigned.io
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.


from time import sleep
import sys
import serial
import threading
import time
import math

class KISS():
    FEND            = 0xC0
    FESC            = 0xDB
    TFEND           = 0xDC
    TFESC           = 0xDD
    CMD_UNKNOWN     = 0xFE
    CMD_DATA        = 0x00
    CMD_FREQUENCY   = 0x01
    CMD_BANDWIDTH   = 0x02
    CMD_TXPOWER     = 0x03
    CMD_SF          = 0x04
    CMD_CR          = 0x05
    CMD_RADIO_STATE = 0x06
    CMD_RADIO_LOCK  = 0x07
    CMD_DETECT      = 0x08
    CMD_PROMISC     = 0x0E
    CMD_READY       = 0x0F
    CMD_STAT_RX     = 0x21
    CMD_STAT_TX     = 0x22
    CMD_STAT_RSSI   = 0x23
    CMD_STAT_SNR    = 0x24
    CMD_BLINK       = 0x30
    CMD_RANDOM      = 0x40
    CMD_FW_VERSION  = 0x50
    CMD_ROM_READ    = 0x51

    DETECT_REQ      = 0x73
    DETECT_RESP     = 0x46

    RADIO_STATE_OFF = 0x00
    RADIO_STATE_ON  = 0x01
    RADIO_STATE_ASK = 0xFF
    
    CMD_ERROR           = 0x90
    ERROR_INITRADIO     = 0x01
    ERROR_TXFAILED      = 0x02
    ERROR_EEPROM_LOCKED = 0x03

    @staticmethod
    def escape(data):
        data = data.replace(bytes([0xdb]), bytes([0xdb, 0xdd]))
        data = data.replace(bytes([0xc0]), bytes([0xdb, 0xdc]))
        return data
    

class RNodeInterface():
    MTU       = 500
    MAX_CHUNK = 32768
    FREQ_MIN  = 137000000
    FREQ_MAX  = 1020000000

    LOG_CRITICAL = 0
    LOG_ERROR    = 1
    LOG_WARNING  = 2
    LOG_NOTICE   = 3
    LOG_INFO     = 4
    LOG_VERBOSE  = 5
    LOG_DEBUG    = 6
    LOG_EXTREME  = 7

    FREQ_MIN = 137000000
    FREQ_MAX = 1020000000

    RSSI_OFFSET = 157

    CALLSIGN_MAX_LEN    = 32

    def __init__(self, callback, name, port, frequency = None, bandwidth = None, txpower = None, sf = None, cr = None, loglevel = LOG_NOTICE, flow_control = False, id_interval = None, id_callsign = None):
        self.serial      = None
        self.loglevel    = loglevel
        self.callback    = callback
        self.name        = name
        self.port        = port
        self.speed       = 115200
        self.databits    = 8
        self.parity      = serial.PARITY_NONE
        self.stopbits    = 1
        self.timeout     = 100
        self.online      = False

        self.frequency   = frequency
        self.bandwidth   = bandwidth
        self.txpower     = txpower
        self.sf          = sf
        self.cr          = cr
        self.state       = KISS.RADIO_STATE_OFF
        self.bitrate     = 0

        self.last_id     = 0

        self.r_frequency = None
        self.r_bandwidth = None
        self.r_txpower   = None
        self.r_sf        = None
        self.r_cr        = None
        self.r_state     = None
        self.r_lock      = None
        self.r_stat_rx   = None
        self.r_stat_tx   = None
        self.r_stat_rssi = None
        self.r_stat_snr  = None
        self.r_random    = None

        self.packet_queue    = []
        self.flow_control    = flow_control
        self.interface_ready = False

        self.validcfg  = True
        if (self.frequency < RNodeInterface.FREQ_MIN or self.frequency > RNodeInterface.FREQ_MAX):
            self.log("Invalid frequency configured for "+str(self), RNodeInterface.LOG_ERROR)
            self.validcfg = False

        if (self.txpower < 0 or self.txpower > 17):
            self.log("Invalid TX power configured for "+str(self), RNodeInterface.LOG_ERROR)
            self.validcfg = False

        if (self.bandwidth < 7800 or self.bandwidth > 500000):
            self.log("Invalid bandwidth configured for "+str(self), RNodeInterface.LOG_ERROR)
            self.validcfg = False

        if (self.sf < 7 or self.sf > 12):
            self.log("Invalid spreading factor configured for "+str(self), RNodeInterface.LOG_ERROR)
            self.validcfg = False

        if (self.cr < 5 or self.cr > 8):
            self.log("Invalid coding rate configured for "+str(self), RNodeInterface.LOG_ERROR)
            self.validcfg = False

        if id_interval != None and id_callsign != None:
            if (len(id_callsign.encode("utf-8")) <= RNodeInterface.CALLSIGN_MAX_LEN):
                self.should_id = True
                self.id_callsign = id_callsign
                self.id_interval = id_interval
            else:
                self.log("The encoded ID callsign for "+str(self)+" exceeds the max length of "+str(RNodeInterface.CALLSIGN_MAX_LEN)+" bytes.", RNodeInterface.LOG_ERROR)
                self.validcfg = False
        else:
            self.id_interval = None
            self.id_callsign = None

        if (not self.validcfg):
            raise ValueError("The configuration for "+str(self)+" contains errors, interface is offline")

        try:
            self.log("Opening serial port "+self.port+"...")
            self.serial = serial.Serial(
                port = self.port,
                baudrate = self.speed,
                bytesize = self.databits,
                parity = self.parity,
                stopbits = self.stopbits,
                xonxoff = False,
                rtscts = False,
                timeout = 0,
                inter_byte_timeout = None,
                write_timeout = None,
                dsrdtr = False,
            )
        except Exception as e:
            self.log("Could not open serial port for interface "+str(self), RNodeInterface.LOG_ERROR)
            raise e

        if self.serial.is_open:
            sleep(2.0)
            thread = threading.Thread(target=self.readLoop)
            thread.setDaemon(True)
            thread.start()
            self.online = True
            self.log("Serial port "+self.port+" is now open")
            self.log("Configuring RNode interface...", RNodeInterface.LOG_VERBOSE)
            self.initRadio()
            if (self.validateRadioState()):
                self.interface_ready = True
                self.log(str(self)+" is configured and powered up")
                sleep(1.0)
            else:
                self.log("After configuring "+str(self)+", the reported radio parameters did not match your configuration.", RNodeInterface.LOG_ERROR)
                self.log("Make sure that your hardware actually supports the parameters specified in the configuration", RNodeInterface.LOG_ERROR)
                self.log("Aborting RNode startup", RNodeInterface.LOG_ERROR)
                self.serial.close()
                raise IOError("RNode interface did not pass validation")
        else:
            raise IOError("Could not open serial port")

    def log(self, message, level):
        pass

    def initRadio(self):
        self.setFrequency()
        self.setBandwidth()
        self.setTXPower()
        self.setSpreadingFactor()
        self.setCodingRate()
        self.setRadioState(KISS.RADIO_STATE_ON)

    def setFrequency(self):
        c1 = self.frequency >> 24
        c2 = self.frequency >> 16 & 0xFF
        c3 = self.frequency >> 8 & 0xFF
        c4 = self.frequency & 0xFF
        data = KISS.escape(bytes([c1])+bytes([c2])+bytes([c3])+bytes([c4]))

        kiss_command = bytes([KISS.FEND])+bytes([KISS.CMD_FREQUENCY])+data+bytes([KISS.FEND])
        written = self.serial.write(kiss_command)
        if written != len(kiss_command):
            raise IOError("An IO error occurred while configuring frequency for "+self(str))

    def setBandwidth(self):
        c1 = self.bandwidth >> 24
        c2 = self.bandwidth >> 16 & 0xFF
        c3 = self.bandwidth >> 8 & 0xFF
        c4 = self.bandwidth & 0xFF
        data = KISS.escape(bytes([c1])+bytes([c2])+bytes([c3])+bytes([c4]))

        kiss_command = bytes([KISS.FEND])+bytes([KISS.CMD_BANDWIDTH])+data+bytes([KISS.FEND])
        written = self.serial.write(kiss_command)
        if written != len(kiss_command):
            raise IOError("An IO error occurred while configuring bandwidth for "+self(str))

    def setTXPower(self):
        txp = bytes([self.txpower])
        kiss_command = bytes([KISS.FEND])+bytes([KISS.CMD_TXPOWER])+txp+bytes([KISS.FEND])
        written = self.serial.write(kiss_command)
        if written != len(kiss_command):
            raise IOError("An IO error occurred while configuring TX power for "+self(str))

    def setSpreadingFactor(self):
        sf = bytes([self.sf])
        kiss_command = bytes([KISS.FEND])+bytes([KISS.CMD_SF])+sf+bytes([KISS.FEND])
        written = self.serial.write(kiss_command)
        if written != len(kiss_command):
            raise IOError("An IO error occurred while configuring spreading factor for "+self(str))

    def setCodingRate(self):
        cr = bytes([self.cr])
        kiss_command = bytes([KISS.FEND])+bytes([KISS.CMD_CR])+cr+bytes([KISS.FEND])
        written = self.serial.write(kiss_command)
        if written != len(kiss_command):
            raise IOError("An IO error occurred while configuring coding rate for "+self(str))

    def setRadioState(self, state):
        kiss_command = bytes([KISS.FEND])+bytes([KISS.CMD_RADIO_STATE])+bytes([state])+bytes([KISS.FEND])
        written = self.serial.write(kiss_command)
        if written != len(kiss_command):
            raise IOError("An IO error occurred while configuring radio state for "+self(str))

    def validateRadioState(self):
        self.log("Validating radio configuration for "+str(self)+"...", RNodeInterface.LOG_VERBOSE)
        sleep(0.25);
        if (self.frequency != self.r_frequency):
            self.log("Frequency mismatch", RNodeInterface.LOG_ERROR)
            self.validcfg = False
        if (self.bandwidth != self.r_bandwidth):
            self.log("Bandwidth mismatch", RNodeInterface.LOG_ERROR)
            self.validcfg = False
        if (self.txpower != self.r_txpower):
            self.log("TX power mismatch", RNodeInterface.LOG_ERROR)
            self.validcfg = False
        if (self.sf != self.r_sf):
            self.log("Spreading factor mismatch", RNodeInterface.LOG_ERROR)
            self.validcfg = False

        if (self.validcfg):
            return True
        else:
            return False

    def setPromiscuousMode(self, state):
        if state == True:
            kiss_command = bytes([KISS.FEND,KISS.CMD_PROMISC, 0x01, KISS.FEND])
        else:
            kiss_command = bytes([KISS.FEND,KISS.CMD_PROMISC, 0x00, KISS.FEND])

        written = self.serial.write(kiss_command)
        if written != len(kiss_command):
            raise IOError("An IO error occurred while configuring promiscuous mode for "+self(str))


    def updateBitrate(self):
        try:
            self.bitrate = self.r_sf * ( (4.0/self.r_cr) / (math.pow(2,self.r_sf)/(self.r_bandwidth/1000)) ) * 1000
            self.bitrate_kbps = round(self.bitrate/1000.0, 2)
            self.log(str(self)+" On-air bitrate is now "+str(self.bitrate_kbps)+ " kbps", RNodeInterface.LOG_DEBUG)
        except:
            self.bitrate = 0

    def processIncoming(self, data):
        self.callback(data, self)

    def send(self, data):
        self.processOutgoing(data)

    def processOutgoing(self,data):
        if self.online:
            if self.interface_ready:
                if self.flow_control:
                    self.interface_ready = False

                frame = b""

                if self.id_interval != None and self.id_callsign != None:
                    if self.last_id + self.id_interval < time.time():
                        self.last_id = time.time()
                        frame = bytes([0xc0])+bytes([0x00])+KISS.escape(self.id_callsign.encode("utf-8"))+bytes([0xc0])

                data    = KISS.escape(data)
                frame  += bytes([0xc0])+bytes([0x00])+data+bytes([0xc0])
                written = self.serial.write(frame)

                if written != len(frame):
                    raise IOError("Serial interface only wrote "+str(written)+" bytes of "+str(len(data)))
            else:
                self.queue(data)

    def queue(self, data):
        self.packet_queue.append(data)

    def process_queue(self):
        if len(self.packet_queue) > 0:
            data = self.packet_queue.pop(0)
            self.interface_ready = True
            self.processOutgoing(data)
        elif len(self.packet_queue) == 0:
            self.interface_ready = True

    def readLoop(self):
        try:
            in_frame = False
            escape = False
            command = KISS.CMD_UNKNOWN
            data_buffer = b""
            command_buffer = b""
            last_read_ms = int(time.time()*1000)

            while self.serial.is_open:
                if self.serial.in_waiting:
                    byte = ord(self.serial.read(1))
                    last_read_ms = int(time.time()*1000)

                    if (in_frame and byte == KISS.FEND and command == KISS.CMD_DATA):
                        in_frame = False
                        self.processIncoming(data_buffer)
                        data_buffer = b""
                        command_buffer = b""
                    elif (byte == KISS.FEND):
                        in_frame = True
                        command = KISS.CMD_UNKNOWN
                        data_buffer = b""
                        command_buffer = b""
                    elif (in_frame and len(data_buffer) < RNodeInterface.MTU):
                        if (len(data_buffer) == 0 and command == KISS.CMD_UNKNOWN):
                            command = byte
                        elif (command == KISS.CMD_DATA):
                            if (byte == KISS.FESC):
                                escape = True
                            else:
                                if (escape):
                                    if (byte == KISS.TFEND):
                                        byte = KISS.FEND
                                    if (byte == KISS.TFESC):
                                        byte = KISS.FESC
                                    escape = False
                                data_buffer = data_buffer+bytes([byte])
                        elif (command == KISS.CMD_FREQUENCY):
                            if (byte == KISS.FESC):
                                escape = True
                            else:
                                if (escape):
                                    if (byte == KISS.TFEND):
                                        byte = KISS.FEND
                                    if (byte == KISS.TFESC):
                                        byte = KISS.FESC
                                    escape = False
                                command_buffer = command_buffer+bytes([byte])
                                if (len(command_buffer) == 4):
                                    self.r_frequency = command_buffer[0] << 24 | command_buffer[1] << 16 | command_buffer[2] << 8 | command_buffer[3]
                                    self.log(str(self)+" Radio reporting frequency is "+str(self.r_frequency/1000000.0)+" MHz", RNodeInterface.LOG_DEBUG)
                                    self.updateBitrate()

                        elif (command == KISS.CMD_BANDWIDTH):
                            if (byte == KISS.FESC):
                                escape = True
                            else:
                                if (escape):
                                    if (byte == KISS.TFEND):
                                        byte = KISS.FEND
                                    if (byte == KISS.TFESC):
                                        byte = KISS.FESC
                                    escape = False
                                command_buffer = command_buffer+bytes([byte])
                                if (len(command_buffer) == 4):
                                    self.r_bandwidth = command_buffer[0] << 24 | command_buffer[1] << 16 | command_buffer[2] << 8 | command_buffer[3]
                                    self.log(str(self)+" Radio reporting bandwidth is "+str(self.r_bandwidth/1000.0)+" KHz", RNodeInterface.LOG_DEBUG)
                                    self.updateBitrate()

                        elif (command == KISS.CMD_TXPOWER):
                            self.r_txpower = byte
                            self.log(str(self)+" Radio reporting TX power is "+str(self.r_txpower)+" dBm", RNodeInterface.LOG_DEBUG)
                        elif (command == KISS.CMD_SF):
                            self.r_sf = byte
                            self.log(str(self)+" Radio reporting spreading factor is "+str(self.r_sf), RNodeInterface.LOG_DEBUG)
                            self.updateBitrate()
                        elif (command == KISS.CMD_CR):
                            self.r_cr = byte
                            self.log(str(self)+" Radio reporting coding rate is "+str(self.r_cr), RNodeInterface.LOG_DEBUG)
                            self.updateBitrate()
                        elif (command == KISS.CMD_RADIO_STATE):
                            self.r_state = byte
                        elif (command == KISS.CMD_RADIO_LOCK):
                            self.r_lock = byte
                        elif (command == KISS.CMD_STAT_RX):
                            if (byte == KISS.FESC):
                                escape = True
                            else:
                                if (escape):
                                    if (byte == KISS.TFEND):
                                        byte = KISS.FEND
                                    if (byte == KISS.TFESC):
                                        byte = KISS.FESC
                                    escape = False
                                command_buffer = command_buffer+bytes([byte])
                                if (len(command_buffer) == 4):
                                    self.r_stat_rx = ord(command_buffer[0]) << 24 | ord(command_buffer[1]) << 16 | ord(command_buffer[2]) << 8 | ord(command_buffer[3])

                        elif (command == KISS.CMD_STAT_TX):
                            if (byte == KISS.FESC):
                                escape = True
                            else:
                                if (escape):
                                    if (byte == KISS.TFEND):
                                        byte = KISS.FEND
                                    if (byte == KISS.TFESC):
                                        byte = KISS.FESC
                                    escape = False
                                command_buffer = command_buffer+bytes([byte])
                                if (len(command_buffer) == 4):
                                    self.r_stat_tx = ord(command_buffer[0]) << 24 | ord(command_buffer[1]) << 16 | ord(command_buffer[2]) << 8 | ord(command_buffer[3])

                        elif (command == KISS.CMD_STAT_RSSI):
                            self.r_stat_rssi = byte-RNodeInterface.RSSI_OFFSET
                        elif (command == KISS.CMD_STAT_SNR):
                            self.r_stat_snr = int.from_bytes(bytes([byte]), byteorder="big", signed=True) * 0.25
                        elif (command == KISS.CMD_RANDOM):
                            self.r_random = byte
                        elif (command == KISS.CMD_ERROR):
                            if (byte == KISS.ERROR_INITRADIO):
                                self.log(str(self)+" hardware initialisation error (code "+RNS.hexrep(byte)+")", RNodeInterface.LOG_ERROR)
                            elif (byte == KISS.ERROR_INITRADIO):
                                self.log(str(self)+" hardware TX error (code "+RNS.hexrep(byte)+")", RNodeInterface.LOG_ERROR)
                            else:
                                self.log(str(self)+" hardware error (code "+RNS.hexrep(byte)+")", RNodeInterface.LOG_ERROR)
                        elif (command == KISS.CMD_READY):
                            self.process_queue()
                        
                else:
                    time_since_last = int(time.time()*1000) - last_read_ms
                    if len(data_buffer) > 0 and time_since_last > self.timeout:
                        self.log(str(self)+" serial read timeout", RNodeInterface.LOG_DEBUG)
                        data_buffer = b""
                        in_frame = False
                        command = KISS.CMD_UNKNOWN
                        escape = False
                    sleep(0.08)

        except Exception as e:
            self.online = False
            self.log("A serial port error occurred, the contained exception was: "+str(e), RNodeInterface.LOG_ERROR)
            self.log("The interface "+str(self.name)+" is now offline.", RNodeInterface.LOG_ERROR)

    def log(self, msg, level=3):
        logtimefmt   = "%Y-%m-%d %H:%M:%S"
        if self.loglevel >= level:
            timestamp = time.time()
            logstring = "["+time.strftime(logtimefmt)+"] ["+self.loglevelname(level)+"] "+msg
            print(logstring)

    def loglevelname(self, level):
        if (level == RNodeInterface.LOG_CRITICAL):
            return "Critical"
        if (level == RNodeInterface.LOG_ERROR):
            return "Error"
        if (level == RNodeInterface.LOG_WARNING):
            return "Warning"
        if (level == RNodeInterface.LOG_NOTICE):
            return "Notice"
        if (level == RNodeInterface.LOG_INFO):
            return "Info"
        if (level == RNodeInterface.LOG_VERBOSE):
            return "Verbose"
        if (level == RNodeInterface.LOG_DEBUG):
            return "Debug"
        if (level == RNodeInterface.LOG_EXTREME):
            return "Extra"

    def hexrep(data, delimit=True):
        delimiter = ":"
        if not delimit:
            delimiter = ""
        hexrep = delimiter.join("{:02x}".format(ord(c)) for c in data)
        return hexrep

    def __str__(self):
        return "RNodeInterface["+self.name+"]"

