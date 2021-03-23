#!/usr/bin/env python

"""
Copyright(C) 2021, BrucesHobbies
All Rights Reserved

AUTHOR: BrucesHobbies
DATE: 03/23/2021
REVISION HISTORY
  DATE        AUTHOR          CHANGES
  yyyy/mm/dd  --------------- -------------------------------------


GENERAL INFO
  energyMaster is designed to monitor and log energy consumption from home devices. Enery is monitored
  using low-cost PZEM modules which are connected by a single twisted pair (2-conductor) low voltage
  RS-485 than can run over 1,000 ft or 300 meters to a USB dongle in a low-cost Raspberry Pi (RPi).

  EnergyMaster supports multiple databases including
  - Comma Separated Variable (CSV) which makes import in spreadsheets easy
  - InfluxDB
  - SQL
  - MQTT publish/subscribe messaging

  EnergyMaster will generate status and alert emails that can be sent to another email or as an SMS text
  to your cell phone when abnormal runtime, or power useage is detected.

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

Logging of data to Comma Separated Variable (CSV)files, InfluxDB, SQL, or MQTT 
  - Energy perspective (tLog minutes default, long term log): logEnergy.csv
  - Details of on-time (tInterval seconds default, short term log): logDetails_chan_name.csv
  - Preventative maintenance (end of on state): logStats_chan_name.csv (alg.py)

Period stats:
  Daily:
    number of cycles
    min run time
    max run time
    total run time
    power
  Per on cycle:
    average time
    standard deviation of runtime
    average power
    standard deviation power

Power alerts:
  out of range power/HP/wattage
  exceeding n*stdev()

Run Time Alerts
  exceed run time
  exceeding n*stdev()

Displays and logs to csv file, MQTT, etc.:
  Current instant time, and motor column label
  -- voltage (V), amperage (A), power (W-Hr), freq (Hz), power factor, and state.
     (Uses power to calc energy and not meter energy summation)
  Current interval: cycles, run time, and power(W-Hr)
  Last interval: cycles, run time, and power(W-Hr)
  Today: cycles, minRunTime, maxRunTime, total run time, power(W-Hr)
  Yesterday: cycles, minRunTime, maxRunTime, total run time, power(W-Hr) 

""" 

import os
import sys
import time
import datetime
from threading import Timer
import math
import subprocess

import pzem             # power meter serial comm
import alg              # algorithms for alerts
import pubScribe


#
# --- User configuration settings --------------------------------------------------
# Configuration settings - modify this section to user needs
# chanNames should not exceed 8 characters
#

##chanNames = ["Device1","Device2","Device3","Device4"]
chanNames = ["Light"]
chanPorts = ["/dev/ttyUSB0", "/dev/ttyUSB1", "/dev/ttyUSB2", "/dev/ttyUSB3"]   # One entry per chanName[]
chanAddrs = [0x01, 0x01, 0x01, 0x01]                                           # One entry per chanName[]
chanOnThresholds = [5, 20, 20, 20]                                 # Watts, with one entry per chanName[]

# Timing parameters
tInterval = 0.5    # time interval in seconds between measuring current
                   # Nominal time on RPi3 is 0.072 seconds, don't go below 0.1 on RPi3 or Zero
tLog = 15          # time interval in minutes between logging energy measurements to csv file

#
# --- User Email Alerts Configuration ---
#
# First time program starts, it will ask you for the sender's email
# this should be an email that you have established for sending alerts from this program
# gmail is suggested with "Less Secure App Access" turned on. This is required for Python on the RPI.
# If you change passwords, please delete emailCfg.json so that this program will again ask for the password.
#

statusMsgEnabled = 0                              # non zero enables sending of email / SMS text messages
statusMsgHHMM    = [12, 0]                        # Status message time to send [hh, mm]

alertMsgEnabled  = 1                              # non zero enables sending of email / SMS text messages
runTimeAlert = [30*60] * len(chanNames)           # Run time to trigger email / SMS text - seconds
##minIntervalBtwEmails = [2*3600] * len(chanNames)  # Wait this long before sending another email - seconds
minIntervalBtwEmails = [600] * len(chanNames)  # Wait this long before sending another email - seconds

# --- END USER CONFIG ---

messageRow = 33
messageText = ""

onTime = [0] * len(chanNames)                     # time motor turned on
maxRuntimeLastEmailTime = [0] * len(chanNames)    # Last time email was sent
algLastEmailTime = [0] * len(chanNames)           # Last time email was sent


#
# Motor Data
#
lastReadTime = 0					# Seconds since epoch


# Current state
lastStateOn = [0] * len(chanNames)         # 0=Off, 1=On
voltage     = [0] * len(chanNames)         # Volts
amperage    = [0] * len(chanNames)         # Amperes
power       = [0] * len(chanNames)         # Watts
energy      = [0] * len(chanNames)         # Watt-hours
frequency   = [0] * len(chanNames)         # Hertz
powerFactor = [0] * len(chanNames)
alarmStatus = [0] * len(chanNames)         # See supplier docs

# Current interval
cycles        = [0] * len(chanNames)       # Off-On state changes
runTime       = [0] * len(chanNames)       # Run time in interval - seconds
powerConsumed = [0] * len(chanNames)       # Watt-hours

# Last interval
cyclesLastInterval        = [0] * len(chanNames)
runTimeLastInterval       = [0] * len(chanNames)
powerConsumedLastInterval = [0] * len(chanNames)

# Today
cyclesToday        = [0] * len(chanNames)
runTimeToday       = [0] * len(chanNames)
powerConsumedToday = [0] * len(chanNames)
minRunTimeToday    = [0] * len(chanNames)
maxRunTimeToday    = [0] * len(chanNames)

# Yesterday
cyclesYesterday        = [0] * len(chanNames)
runTimeYesterday       = [0] * len(chanNames)
powerConsumedYesterday = [0] * len(chanNames)
minRunTimeYesterday    = [0] * len(chanNames)
maxRunTimeYesterday    = [0] * len(chanNames)



#
# Trim log files to prevent unbounded growth over years
#
def trimLogs(logfilename, rows=48*3600/tInterval) :
    rc = subprocess.call("echo \"$(tail -n " + "{}".format(int(rows)) + " " + logfilename + ")\" > " + logfilename, shell=True)


#
# Display control
# http://ascii-table.com/ansi-escape-sequences-vt-100.php
#
def clearWindow() : 
    #define clear() printf("\033[H\033[J")
    # ESC[H moves cursor to top left corner
    # ESC[J clears screen from the cursor to the end of screen
    print("\033[H\033[J")	

def clearDown() :
    print("\033[J")

def printRowCol(row,col,arg="") :
    CSI = "\033["
    #sys.stdout.write( CSI + str(row) + ";" + str(col) + 'H' + str(arg))
    print(CSI + str(row) + ";" + str(col) + 'H' + str(arg))

def formatTime(seconds): 
    # return str(datetime.timedelta(seconds = seconds))
    return time.strftime("%H:%M:%S", time.gmtime(seconds)) 

def formatLocalTime() :
    # timeStr = str(datetime.datetime.now())    # yyyy-mm-dd hh:mm:ss.ssssss
    # return timeStr[:-7]
    return time.strftime("%a, %Y-%b-%d, %H:%M:%S", time.localtime())	#%b=abbr mo, %B=mo name, %m=m as decimal


#
# Read Power
#
def readPower() :
    global lastReadTime
    global lastStateOn, onTime
    global voltage, amperage, power, energy, frequency, powerFactor, alarmStatus
    global cycles, runTime, powerConsumed
    global cyclesToday, runTimeToday, powerConsumedToday, minRunTimeToday, maxRunTimeToday
    global maxRuntimeLastEmailTime, messageText

    t = time.time()
    timeDelta = (t-lastReadTime)
    if timeDelta > tInterval*10 :		# Assume first interval is tInterval
        timeDelta = tInterval

    for chan in range(0, len(chanNames)) :
        [voltage[chan], amperage[chan], power[chan], energy[chan], frequency[chan], powerFactor[chan], \
                alarmStatus[chan]] = pzem.readAcPZEM(chanPorts[chan], chanAddrs[chan])

        if (power[chan] > chanOnThresholds[chan]) :
            detailsLog(chan, voltage[chan], amperage[chan], power[chan], energy[chan], frequency[chan], \
                    powerFactor[chan], alarmStatus[chan])

            alg.motorStatsAppend(chan, power[chan])

            runTime[chan] = runTime[chan] + timeDelta
            runTimeToday[chan] = runTimeToday[chan] + timeDelta

            if (lastStateOn[chan]==0) :
                cycles[chan] = cycles[chan] + 1
                lastStateOn[chan] = 1
                cyclesToday[chan] = cyclesToday[chan] + 1
                onTime[chan] = t		# time motor turned on

            elif (alertMsgEnabled and (t > (runTimeAlert[chan] + onTime[chan]))) :
                # Motor on time exceeded threshold
                if (t > (minIntervalBtwEmails[chan])+maxRuntimeLastEmailTime[chan]) :
                    # Allowed to send email text message
                    maxRuntimeLastEmailTime[chan] = t
                    s = chanNames[chan] + " on time exceeded!"
                    sendAlert(chanNames[chan], s)

        elif lastStateOn[chan] :
            lastStateOn[chan] = 0

            rt = t - onTime[chan]
            if minRunTimeToday[chan] == 0 :
                minRunTimeToday[chan] = rt
            elif rt < minRunTimeToday[chan] :
                minRunTimeToday[chan] = rt

            if rt > maxRunTimeToday[chan] :
                maxRunTimeToday[chan] = rt

            hdr, returnStr, alertMsg = alg.motorStats(chan, chanNames, rt, tInterval)

            timeStr = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
            messageText = "{:.2f},{},{}\n{}".format(t, timeStr, returnStr+"        ",alertMsg+"     ")

            if returnStr!="" :
                topic = "energyMaster/logStats_" + chanNames[chan]
                pubScribe.pubRecord(pubScribe.CSV_FILE, topic, returnStr, hdr)

            if alertMsg!="" and alertMsgEnabled and (t > (minIntervalBtwEmails[chan])+algLastEmailTime[chan]) :
                # Allowed to send email text message
                algLastEmailTime[chan] = t
                sendAlert(chanNames[chan], alertMsg)

        if lastReadTime :
            pwr = power[chan] * timeDelta/3600.
            powerConsumed[chan] = powerConsumed[chan] + pwr
            powerConsumedToday[chan] = powerConsumedToday[chan] + pwr

    # end for

    lastReadTime = t


#
# Send alert via email to another email or as SMS text
#
def sendAlert(subj, alertMsg) :
    printRowCol(messageRow,0,"")
    clearDown()
    topic = "energyMaster/Alert"
    pubScribe.pubRecord(pubScribe.EMAIL_SMS, topic, alertMsg)


#
# Send status via email to another email or as SMS text
#
def sendStatus() :
    printRowCol(messageRow,0,"")
    clearDown()
    statusMsg = "Yesterday summary: \n"
    for chan in range(0, len(chanNames)) :
        statusMsg += chanNames[chan] + " Cycles: {:<5.0f} \n".format(cyclesYesterday[chan])
        statusMsg += "MinRunTime: " + formatTime(minRunTimeYesterday[chan]) + '\n'
        statusMsg += "MaxRunTime: " + formatTime(maxRunTimeYesterday[chan]) + '\n'
        statusMsg += "TotalRunTime: " + formatTime(runTimeYesterday[chan]) + '\n'
        statusMsg += "Power (Wh): {:<8.2f} \n\n".format(powerConsumedYesterday[chan])
    topic = "energyMaster/Status"
    pubScribe.pubRecord(pubScribe.EMAIL_SMS, topic, statusMsg)


#
# Append interval data to CSV file
#
def energyLog():
    hdr = ""
    for name in chanNames :
        hdr += name + " cycles" + "," + name + " (Wh)" + ","
    hdr = hdr[:-1]

    s = ""
    for chan in range(0, len(chanNames)) :
        s += str(round(cycles[chan])) + "," + str(round(powerConsumed[chan], 2)) + ","
    s = s[:-1]

    topic = "energyMaster/logEnergy"
    pubScribe.pubRecord(pubScribe.CSV_FILE, topic, s, hdr)


#
# Logs readings to csv file
#
def detailsLog(chan, voltage, amperage, power, energy, frequency, powerFactor, alarmStatus):
    hdr = 'Volts,Amps,Watts,Energy (Wh),Freq (Hz),PF,Status'
    s = "{:.0f},{:.1f},{:.1f},{:.1f},{:.1f},{:.1f},{:.1f},{:.0f}".format(chan, voltage, amperage, power, energy, frequency, powerFactor, alarmStatus)
    topic = "energyMaster/logDetails_" + chanNames[chan]
    pubScribe.pubRecord(pubScribe.CSV_FILE, topic, s, hdr)


#
# Start timer
#
def startTimer():
    global timer
    t = datetime.datetime.now()
    Timer(tInterval - (t.microsecond/1000000.)%tInterval, myTimer).start()	# next tInterval seconds


#
# tInterval timer
#
stopFlag = 0

def myTimer() :
    global timer

    global lastReadTime
    global voltage, amperage, power, energy, frequency, powerFactor, alarmStatus
    global cycles, runTime, powerConsumed
    global cyclesLastInterval, runTimeLastInterval, powerConsumedLastInterval
    global cyclesToday, runTimeToday, powerConsumedToday, minRunTimeToday, maxRunTimeToday
    global cyclesYesterday, runTimeYesterday, powerConsumedYesterday, minRunTimeYesterday, maxRunTimeYesterday
   
    t = datetime.datetime.now()
    firstSec = t.microsecond < (tInterval*1000000./2.)

    # move TODAY data to YESTERDAY
    if (t.hour==0 and t.minute==0 and t.second==0 and firstSec) :
        runTimeYesterday = runTimeToday
        runTimeToday = [0] * len(chanNames)

        cyclesYesterday = cyclesToday
        cyclesToday = [0] * len(chanNames)

        powerConsumedYesterday = powerConsumedToday
        powerConsumedToday = [0] * len(chanNames)

        minRunTimeYesterday = minRunTimeToday
        minRunTimeToday = [0] * len(chanNames)

        maxRunTimeYesterday = maxRunTimeToday
        maxRunTimeToday = [0] * len(chanNames)

    # send daily status email to email or to SMS text
    if (statusMsgEnabled and t.hour==statusMsgHHMM[0] and t.minute==statusMsgHHMM[1] and t.second==5 and firstSec) :
        sendStatus()
    
    # log data and reset counters
    elif ((not (t.minute%tLog)) and (t.second==0) and firstSec) :
        energyLog()

        # copy counters to LastInterval and reset counters
        cyclesLastInterval = cycles
        cycles = [0] * len(chanNames)

        runTimeLastInterval = runTime
        runTime = [0] * len(chanNames)

        powerConsumedLastInterval = powerConsumed
        powerConsumed = [0] * len(chanNames)

    # need to add trim daily log files here

    # read power, skips some intervals to minimize processor load but accounts for double tInterval
    else :
        readPower()

        if firstSec :
            clearWindow()
            displayLabels()
            display()
            displayLastInterval()
            displayYesterday()
            printRowCol(messageRow,0,messageText+"        ")

    if not stopFlag :
        t = datetime.datetime.now()
        Timer(tInterval - (t.microsecond/1000000.)%tInterval, myTimer).start()	# every tInterval seconds



COL_WIDTH = 10    # Column spacing between motors

#
# Display row and column headers
#
def displayLabels() :
    lbl = ["Time: ", "Voltage (V)     :","Amperage (A)    :","Power (W)       :",
        "Frequency (Hz)  :","PowerFactor     :","State           : ","",
        "Current interval ", "          cycles: ",  "      run time  : ",  "      power (Wh): ", "",
        "Last interval ", "          cycles: ",  "      run time  : ",  "      power (Wh): ", "",
        "Today ", "          cycles: ", "    min run time: ", "    max run time: ", "  total run time: ",  "      power (Wh): ", "",
        "Yesterday ", "          cycles: ", "    min run time: ", "    max run time: ", "  total run time: ",  "      power (Wh): ", ""]

    # Column headings
    for chan in range(0, len(chanNames)) :
        col = 20 + COL_WIDTH * chan
        printRowCol(0,col,chanNames[chan])

    # Row headings
    row = 1
    for item in lbl :
        printRowCol(row,0,item)
        row = row + 1


#
# Display INSTANTANEOUS, CURRENT INTERVAL, and TODAY
#
def display() :
    # Display current time
    printRowCol(0, 7, time.strftime("%H:%M:%S", time.localtime()))
    
    for chan in range(0, len(chanNames)) :
        col = 20 + COL_WIDTH * chan
        # Display instantaneous
        printRowCol(2, col, "{: 8.1f}  ".format(voltage[chan]))
        printRowCol(3, col, "{: 8.3f}  ".format(amperage[chan]))
        printRowCol(4, col, "{: 8.1f}  ".format(power[chan]))
        printRowCol(5, col, "{: 8.1f}  ".format(frequency[chan]))
        printRowCol(6, col, "{: 8.2f}  ".format(powerFactor[chan]))
        printRowCol(7, col, "{: 8.0f}  ".format(lastStateOn[chan]))

        # Display CURRENT INTERVAL
        printRowCol(10, col, "{:<5.0f} ".format(cycles[chan]))
        printRowCol(11, col, formatTime(runTime[chan]))
        printRowCol(12, col, "{:<8.2f} ".format(powerConsumed[chan]))

        # Display TODAY
        printRowCol(20, col, "{:<5.0f} ".format(cyclesToday[chan]))
        printRowCol(21, col, formatTime(minRunTimeToday[chan]))
        printRowCol(22, col, formatTime(maxRunTimeToday[chan]))
        printRowCol(23, col, formatTime(runTimeToday[chan]))
        printRowCol(24, col, "{:<8.2f} ".format(powerConsumedToday[chan]))


#
# Update display of LAST INTERVAL
#
def displayLastInterval() :
    for chan in range(0, len(chanNames)) :
        col = 20 + COL_WIDTH * chan
        printRowCol(15, col, "{:<5.0f} ".format(cyclesLastInterval[chan]))
        printRowCol(16, col, formatTime(runTimeLastInterval[chan]))
        printRowCol(17, col, "{:<8.2f} ".format(powerConsumedLastInterval[chan]))


#
# Update display of YESTERDAY
#
def displayYesterday() :
    for chan in range(0, len(chanNames)) :
        col = 20 + COL_WIDTH * chan
        printRowCol(27, col, "{:<5.0f} ".format(cyclesYesterday[chan]))
        printRowCol(28, col, formatTime(minRunTimeYesterday[chan]))
        printRowCol(29, col, formatTime(maxRunTimeYesterday[chan]))
        printRowCol(30, col, formatTime(runTimeYesterday[chan]))
        printRowCol(31, col, "{:<8.2f} ".format(powerConsumedYesterday[chan]))
    

#---------------------------------------------------------------------------
if __name__ == '__main__':

    min_tInterval = 1./(10//len(chanNames))
    if tInterval < min_tInterval :
        tInterval = min_tInterval
        print("Setting tInterval to: " + str(tInterval))
        time.sleep(3)

    clearWindow()
    displayLabels()
    print("\nPress CTRL+C to exit...\nMake sure text window is large enough to avoid scrolling.\n")

    if (len(chanNames) > len(chanPorts)) or (len(chanNames) > len(chanAddrs)) or (len(chanNames) > len(chanOnThresholds)) :
        print("ERROR: number of chanNames and chanPorts or chanOnThresholds")
        sys.exit("Exit")

    pubScribe.connectPubScribe()

    """
    if statusMsgEnabled :
        # Add instantaneous power status?
        printRowCol(messageRow,0)
        clearDown()
        topic = "energyMaster/Status"
        pubScribe.pubRecord(pubScribe.EMAIL_SMS, topic, "Program start")
    """

    alg.calAlgInit(chanNames)

    startTimer()

    try:
        while(True):
            time.sleep(1)

    except KeyboardInterrupt:
        #timer.cancel()
        stopFlag = 1

        clearDown()
        print("Exiting...")

    pubScribe.disconnectPubScribe()

