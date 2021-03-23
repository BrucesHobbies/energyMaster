#!/usr/bin/env python

"""
Copyright(C) 2021, BrucesHobbies
All Rights Reserved

AUTHOR: Bruce
DATE: 3/23/2021
REVISION HISTORY
  DATE        AUTHOR          CHANGES
  yyyy/mm/dd  --------------- -------------------------------------


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


SIGMA USER CONFIGURATION (Option A - self learning)

  Load should be fairly constant ignoring startup and wind down time for certain applications

  Load on time should be fairly constant for certain applications


HP USER CONFIGURATION (Option B - based on user entry of motor HP or watts)

  Electric motors are typically most efficient at 75% load.
    Efficiency drops off dramatically at less than 50% load (underloaded).
    Motor operation at over 115% is not good (overloaded / overheating).

  If your motor runs under 50% or over 115%, the motor or pump may be incorrectly sized. 
  The initial settings are 50% and 115%. You may adjust narrower based on run data collected.

"""

import os
import time
import datetime


HP2WATTS = 745.7            # HP to Watts
WATTS2HP = (1.0/HP2WATTS)   # Watts to HP

try :
    import json
except ImportError :
    try :
        import simplejson as json
    except ImportError :
        print("Error: import json module failed")
        sys.exit()

encoding = 'utf-8'

cfgAlgFileName = 'cfgAlg.json'

#
# Default settings for all motors, modify inidividual motors in algInit()...
#
cfgAlg = {
    u"startupTime": 2,
    u"shutdownTime": 2,

    # Number of motor cycles to establish means and standard deviations
    u"SIGMA_MOTOR_CYCLES": 21,

    # Lower sigma bound is tighter threshold, but more false positives
    u"RUNTIME_SIGMA_ALG_ENABLE": 0,
    u"RUNTIME_SIGMA_BOUND": 3.0,

    u"runtime": [],
    u"meanRuntime": [],
    u"stdevRuntime": [],

    # Lower sigma bound is tighter threshold, but more false positives
    u"POWER_SIGMA_ALG_ENABLE": 0,
    u"POWER_SIGMA_BOUND": 3.0,     

    u"power": [],
    u"meanPower": [],
    u"stdevPower": [],

    u"HP_ALG_ENABLE": 0,       # Use HP for alerts
    u"MOTOR_HP": 0.5,          # Motor size in HP
    u"MOTOR_LOW_HP": 0.5,      # Motors are extremely inefficient at less than 50%
    u"MOTOR_HIGH_HP": 1.15     # Most motors should not go over 115%
}


motorAlgs = {}                 # Summary of on state power for motors
powerSeries = []               # Motor profiles during on state


#
# Algorithms initialize, reload previous cal data if it exists
#
def calAlgInit(chanNames) : 
    global motorAlgs, powerSeries

    motorAlgs = {name : cfgAlg for name in chanNames}
    powerSeries = [[] for _ in range(len(chanNames))]

    try :
        with open(cfgAlgFileName, 'r') as cfgAlgFile :
            cfgAlg_temp = json.load(cfgAlgFile)
            # Replace default values with values from file
            for motor in motorAlgs:  
                if motor in cfgAlg_temp :
                    for item in motorAlgs[motor] :
                        if item in cfgAlg_temp[motor] :
                            motorAlgs[motor][item] = cfgAlg_temp[motor][item]
            
    # If file does not exist, it will be created using defaults.
    except IOError :
        print(cfgAlgFileName + " does not exist. File will be created.")

    # === BEGIN USER CONFIGURATION OVERRIDES =======================================
    # Examples...
    # Option A: Sigma method
    motorAlgs[chanNames[0]]["SIGMA_MOTOR_CYCLES"] = 5        ## Number of on-periods to average

    motorAlgs[chanNames[0]]["POWER_SIGMA_ALG_ENABLE"] = 1    ## Enabled
    motorAlgs[chanNames[0]]["POWER_SIGMA_BOUND"] = 1.0       ## Changed from 3.0 to 1.0

    motorAlgs[chanNames[0]]["RUNTIME_SIGMA_ALG_ENABLE"] = 1  ## Enabled
    motorAlgs[chanNames[0]]["RUNTIME_SIGMA_BOUND"] = 1.0     ## Changed from 3.0 to 1.0

    motorAlgs[chanNames[0]]["startupTime"] = 2               ## seconds
    motorAlgs[chanNames[0]]["shutdownTime"] = 2              ## seconds
    
    motorAlgs[chanNames[0]]["HP_ALG_ENABLE"] = 0
    # motorAlgs[chanNames[0]]["MOTOR_HP"] = 2./4.
    # motorAlgs[chanNames[0]]["MOTOR_LOW_HP"] = 0.5
    # motorAlgs[chanNames[0]]["MOTOR_HIGH_HP"] = 1.15

    # Option B: HP/Wattage percent change
    if len(chanNames) > 1 :
        motorAlgs[chanNames[1]]["POWER_SIGMA_ALG_ENABLE"] = 0
        motorAlgs[chanNames[1]]["POWER_SIGMA_BOUND"] = 3.0

        motorAlgs[chanNames[1]]["RUNTIME_SIGMA_ALG_ENABLE"] = 0
        motorAlgs[chanNames[1]]["RUNTIME_SIGMA_BOUND"] = 3.0

        motorAlgs[chanNames[1]]["HP_ALG_ENABLE"] = 0
        motorAlgs[chanNames[1]]["MOTOR_HP"] = 3./4.
        # motorAlgs[chanNames[1]]["MOTOR_LOW_HP"] = 0.5
        # motorAlgs[chanNames[1]]["MOTOR_HIGH_HP"] = 1.15

        motorAlgs[chanNames[1]]["startupTime"] = 120        # Heat start up time in seconds
        motorAlgs[chanNames[1]]["shutdownTime"] = 135       # Heating cool down time in seconds

    # === END USER CONFIGURATION OVERRIDES ==========================================

    return


#
# calAlg() is called at motor on-off transition
# Characterize pump power and runtime, save data to json file.
# Option A, if cal completed, look for out of bounds conditions
# Option B, look for out of bounds conditions
#
def calAlg(chanName, power, runTime) :
    result = ""

    # Option A, calibration
    if len(motorAlgs[chanName]["runtime"]) < motorAlgs[chanName]["SIGMA_MOTOR_CYCLES"] :
        motorAlgs[chanName]["runtime"].append(runTime)
        xdata = motorAlgs[chanName]["runtime"]
        rt_l = len(motorAlgs[chanName]["runtime"])
        mean = sum(xdata) / rt_l
        variance = sum([((x - mean) ** 2) for x in xdata]) / rt_l
        res = variance ** 0.5
        motorAlgs[chanName]["meanRuntime"] = mean
        motorAlgs[chanName]["stdevRuntime"] = res

        motorAlgs[chanName]["power"].append(power)
        xdata = motorAlgs[chanName]["power"]
        pwr_l = len(motorAlgs[chanName]["power"])
        mean = sum(xdata) / pwr_l
        variance = sum([((x - mean) ** 2) for x in xdata]) / pwr_l
        res = variance ** 0.5
        motorAlgs[chanName]["meanPower"] = mean
        motorAlgs[chanName]["stdevPower"] = res

        with open(cfgAlgFileName, 'w') as cfgAlgFile:
            json.dump(motorAlgs, cfgAlgFile)

    # Option A, calibration completed
    else :
        if motorAlgs[chanName]["POWER_SIGMA_ALG_ENABLE"] and \
                (abs(power - motorAlgs[chanName]["meanPower"]) > \
                motorAlgs[chanName]["POWER_SIGMA_BOUND"] * motorAlgs[chanName]["stdevPower"]) :
            result = "Power: " + str(round(power,1)) \
                     + " Exceeded " + str(cfgAlg["POWER_SIGMA_BOUND"]) \
                     + " stdev's of " + str(round(motorAlgs[chanName]["stdevPower"],1)) \
                     + " from mean of " + str(round(motorAlgs[chanName]["meanPower"],1)) + " at initial calibration.\n"

        if motorAlgs[chanName]["RUNTIME_SIGMA_ALG_ENABLE"] \
                and (abs(runTime - motorAlgs[chanName]["meanRuntime"]) \
                > motorAlgs[chanName]["RUNTIME_SIGMA_BOUND"] * motorAlgs[chanName]["stdevRuntime"]) :
            result = result + " Runtime: " + str(round(runTime,1)) \
                     + " Exceeded " + str(motorAlgs[chanName]["RUNTIME_SIGMA_BOUND"]) \
                     + " stdev's of " + str(round(motorAlgs[chanName]["stdevRuntime"],1)) \
                     + " from mean of " + str(round(motorAlgs[chanName]["meanRuntime"],1)) + " at initial calibration.\n"

    # Option B
    if motorAlgs[chanName]["HP_ALG_ENABLE"] :
        if ((power/HP2WATTS) < motorAlgs[chanName]["MOTOR_LOW_HP"]*motorAlgs[chanName]["MOTOR_HP"]) \
                or ((power/HP2WATTS) > motorAlgs[chanName]["MOTOR_HIGH_HP"]*motorAlgs[chanName]["MOTOR_HP"]) :
            result = result + " HP: " + str(round(power/HP2WATTS,3)) + " Exceeded limits of " \
                     + str(round(motorAlgs[chanName]["MOTOR_LOW_HP"]*motorAlgs[chanName]["MOTOR_HP"],3)) + " to " \
                     + str(round(motorAlgs[chanName]["MOTOR_HIGH_HP"]*motorAlgs[chanName]["MOTOR_HP"],3)) + " HP\n"

    return result


#      
# Collect motor profile during on time
#      
def motorStatsAppend(chan, pwr) :
    global powerSeries

    powerSeries[chan].append(pwr)


#      
# Sump Pump / Motor Algorithm
# Called when motor transition from on to off state detected
#
def motorStats(chan, chanNames, runTime, tInterval) :
    global powerSeries

    t = time.time()

    hdr = "Runtime (s),Avg (W),StdDev (W)"

    # Remove motor startup and power down time
    if motorAlgs[chanNames[chan]]["startupTime"] % tInterval :
        start = motorAlgs[chanNames[chan]]["startupTime"] // tInterval + 1
    else :
        start = motorAlgs[chanNames[chan]]["startupTime"] // tInterval

    if motorAlgs[chanNames[chan]]["shutdownTime"] % tInterval :
        end = motorAlgs[chanNames[chan]]["shutdownTime"] // tInterval + 1
    else :
        end = motorAlgs[chanNames[chan]]["shutdownTime"] // tInterval
    
    powerSeries[chan] = powerSeries[chan][int(start):-int(end)]

    # Calculate average power and stdev
    seriesLen = len(powerSeries[chan])
    if seriesLen > 10 :
        meanPwr = sum(powerSeries[chan]) / seriesLen
        variance = sum([((x - meanPwr) ** 2) for x in powerSeries[chan]]) / seriesLen
        res = variance ** 0.5

        rtnString = "{:.1f},{:.1f},{:.1f}".format(runTime, meanPwr, res)
        alertMsg = calAlg(chanNames[chan], meanPwr, runTime)

    else :
        rtnString = ""
        alertMsg = ""

    powerSeries[chan] = []

    return hdr, rtnString, alertMsg


# === Test code ==================================================================
if __name__ == '__main__':

    import numpy as np

    tInterval = 0.5
    chanNames = ["Light"]

    meanPower = 100
    stdPower = 5.0

    meanRuntime = 10
    stdRuntime = 3.0

    calAlgInit(chanNames)
    chan=0

    runtime = 0
    cnt = round((meanRuntime + (stdRuntime * np.random.randn())) / tInterval)
    print(cnt)
    for n in range(cnt) :
        power = meanPower + stdPower * np.random.randn()
        print(power)
        runtime += tInterval
        motorStatsAppend(chan, power)

    hdr, rtnString, alertMsg = motorStats(chan, chanNames, runtime, tInterval)
    print(hdr)
    print(rtnString)
    print(alertMsg)

    print("Done.")
