#!/usr/bin/python3

"""
Author: BrucesHobbies
Copyright(C) 2021 BrucesHobbies
Date: 3/22/2021

REVISION HISTORY
  DATE        AUTHOR          CHANGES
  yyyy/mm/dd  --------------- -------------------------------------


OVERVIEW:
    Read PZEM series AC and DC sensor modules. The AC modules measure
    voltage, current, power, energy, frequency, and power factor. The DC
    modules measure voltage, current, power, energy, and voltage alarm status.

LICENSE:
    This program code and documentation are for personal private use only. 
    No commercial use of this code is allowed without prior written consent.

    This program is free for you to inspect, study, and modify for your 
    personal private use. 

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, version 3 of the License.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <https://www.gnu.org/licenses/>.

GENERAL INFORMATION:
    PREREQUISITES
        sudo pip3 install pymodbus    # Install ModBus 

    VERIFY PZEM MODULE PRESENCE USING RPi COMMAND LINE:
        (once attached by USB cable and RS-485 cable with module power on)
        ls /dev/ttyUSB*    # Show USB devices
        lsusb -v           # Show USB devices with details

PZEM MODULES
Commmunication interface: RS-485
Communication protocol: 9600N81

AC MODULES (80-260V):
  PZEM-014: Measuring Range  10A (Internal shunt)
  PZEM-016: Measuring Range 100A (External shunt supplied with unit)

Voltage:       Measuring range: 80-260V, Resolution: 0.1V, Measurment accuracy: 0.5%
Current:       Measuring range: 0-10A (PZEM-014), 0-100A (PZEM-016)
               Starting measuring current: 0.01A (PZEM-014), 0.02A (PZEM-016)
               Resolution: 0.001A, Measurment accuracy: 0.5%
Active power:  Measuring range: 0-2.3kW (PZEM-014) 0-23kW (PZEM-016)
               Starting measuring power: 0.4W, Resolution: 0.1W
               Format: <1000W one decimal, >=1000W only integer, Measurment accuracy: 0.5%
Power factor:  Measuring range: 0.00-1.00, Resolution: 0.01, Measurment accuracy: 1%
Frequency:     Measuring range: 45-65 Hz, Resolution: 0.1 Hz, Measurment accuracy: 0.5%
Active Energy: Measuring range: 0-999.99 kWh, Resolution: 1 Wh, Measurment accuracy: 0.5%
               Format: <10kWh integer Wh, >=10kWh then kWh

Need to implement set address, alarm threshold, reset energy, and calibration for AC modules.


DC MODULES (7-300V):
(Have not verified all 9 of the DC module software interfaces.)
  PZEM-003        10A Internal shunt
  PZEM-017-3/7    50A External shunt
  PZEM-017-4/8   100A External shunt
  PZEM-017-5/9   200A External shunt
  PZEM-017-6/10  300A External shunt

"""

import pymodbus
import serial
import math

from pymodbus.pdu import ModbusRequest
from pymodbus.client.sync import ModbusSerialClient as ModbusClient
from pymodbus.transaction import ModbusRtuFramer


#
# Bytes to float and apply scale factor
#
def scaleFactor(registers, sf) :
    if len(registers) == 1:
        return registers[0] / sf
    else :
        return ((registers[1] << 8) + registers[0]) / sf


#
# AC Module read
#     chanPort is the USB port - example: "/dev/ttyUSB0"
#     chanAddr is the PZEM module ModBus device address - example: 0x01
#
def readAcPZEM(chanPort, chanAddr) :
    voltage = 0
    amperage = 0
    power = 0
    energy = 0
    frequency = 0
    powerFactor = 0
    alarmStatus = 0

    client = ModbusClient(method = "rtu", port=chanPort, stopbits = 1, bytesize = 8, parity = 'N', baudrate = 9600)
    
    if client.connect() :
        try :
            result = client.read_input_registers (0x0000, 10, unit = chanAddr)
            voltage = scaleFactor (result.registers[0:1], 10)
            amperage = scaleFactor (result.registers[1:3], 1000)
            power = scaleFactor (result.registers[3:5], 10)
            energy = scaleFactor (result.registers[5:7], 1)
            frequency = scaleFactor (result.registers[7:8], 10)
            powerFactor = scaleFactor (result.registers[8:9], 100)
            alarmStatus = int(result.registers[9])

        except Exception as e :
            print('Exception reading AC PZEM: ' + str(e))

        finally :
            client.close()

    return voltage, amperage, power, energy, frequency, powerFactor, alarmStatus


#
# DC Module read
#     chanPort is the USB port - example: "/dev/ttyUSB0"
#     chanAddr is the PZEM module ModBus device address - example: 0x01
#
def readDcPZEM(chanPort, chanAddr) :
    voltage = 0
    amperage = 0
    power = 0
    energy = 0
    highVoltAlarmStatus = 0
    lowVoltAlarmStatus = 0

    #Connect to the serial modbus server
    client = ModbusClient(method = "rtu", port=chanPort, stopbits = 1, bytesize = 8, parity = 'N', baudrate = 9600)
    
    if client.connect ():
        try :
            result = client.read_input_registers (0x0000, 8, unit = chanAddr)
            voltage = scaleFactor(result.registers[0:1], 100)
            amperage = scaleFactor(result.registers[1:2], 100)
            power = scaleFactor(result.registers[2:4], 10)
            energy = scaleFactor(result.registers[4:6], 1)
            highVoltAlarmStatus = int(result.registers[6])
            lowVoltAlarmStatus = int(result.registers[7])

        except Exception as e :
            print('Exception reading DC PZEM: ' + str(e))

        finally :
            client.close()

    return voltage, amperage, power, energy, highVoltAlarmStatus, lowVoltAlarmStatus


def setAddrPowerMeter(chanPort, chanAddr, newChanAddr) :
    print("Not implemented.")
    return

def setAlarmThresholdPowerMeter(chanPort, chanAddr, alarmThreshold) :
    print("Not implemented.")
    return

def resetEnergyPowerMeter(chanPort, chanAddr) :
    print("Not implemented.")
    return

def calibrationPowerMeter(chanPort, chanAddr) :
    print("Not implemented.")
    return


if __name__ == '__main__':
    chanPorts = ["/dev/ttyUSB0", "/dev/ttyUSB1"]
    chanAddrs = [0x01, 0x01]

    chan = 0
    print("Test PZEM-016 module on ", chanPorts[chan], " with channel address of ", chanAddrs[chan], "by performing read of 10 registers:")
    voltage, amperage, power, energy, frequency, powerFactor, alarmStatus = readAcPZEM(chanPorts[chan], chanAddrs[chan])
    print(str(voltage) + 'V')
    print(str(amperage) + 'A')
    print(str(power) + 'W')
    print(str(energy) + 'Wh')
    print(str(frequency) + 'Hz')
    print(str(powerFactor) + " power factor")
    print(str(alarmStatus) + " alarm status")
