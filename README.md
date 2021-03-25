# energyMaster
Energy monitoring for logging, detection of faults, and preventative maintenance monitoring.

Copyright(C) 2021, BrucesHobbies, All Rights Reserved

# energyMaster™ Project Overview
EnergyMaster is designed to monitor and log energy consumption from home devices. Enery is monitored using low-cost PZEM modules which are connected by a single twisted pair (2-conductor) low voltage RS-485 than can run over 1,000 ft or 300 meters to a USB dongle on a low-cost Raspberry Pi (RPi). The devices can be placed centrally near the circuit breaker panel or remotely using the USB RS-485 to the module.

EnergyMaster is designed to detect abnormal operation of electrical devices generating status and alert emails that can be sent to another email or as an SMS text to your cell phone when abnormal runtime or power usage is detected.

Period statistics include:
- Daily:
  - number of cycles
  - min run time
  - max run time
  - total run time
  - power

- Per on cycle statistics include:
  - average run time
  - standard deviation of runtime
  - average power
  - standard deviation of power

Power alerts:
- out of range power/HP/wattage
- exceeding n*stdev()

Run time alerts:
-  exceeding max run time
-  exceeding n*stdev() of typical run time

Displays and logs to csv file, MQTT, etc.:
- Current instant time, and motor column label
  - voltage (V)
  - amperage (A)
  - power (W-Hr)
  - freq (Hz)
  - power factor
  - state
- Current interval: cycles, run time, and power (W-Hr)
- Last interval: cycles, run time, and power (W-Hr)
- Today: cycles, minRunTime, maxRunTime, total run time, power (W-Hr)
- Yesterday: cycles, minRunTime, maxRunTime, total run time, power (W-Hr) 

EnergyMaster supports multiple databases including:
- Comma Separated Variable (CSV) which makes import to spreadsheets easy
- InfluxDB
- SQL
- MQTT publish/subscribe messaging
- Future options
  - IFTT
  - PubNub
  - Twilio
  - Cellular
  - APRS

Send status and alert messages via email or SMS to a cell phone
- Email
- SMS text message to your cell phone

An example Python script is included that plots the power cycles and consumption used by various devices over varying time periods such as 48-hours, 2-weeks, monthly, and yearly.

Monitoring of device energy is done through a PZEM module.

![Figure 1: PZEM](https://github.com/BrucesHobbies/energyMaster/blob/main/figures/figure1.png)

Consult an electrician for your local electrical codes. Also refer to the documentation that comes with the PZEM module. For devices powered off household Alternating Current (AC), either 120 or 240 volt, the PZEM uses a split Current Transformer (CT) to measure current flowing through a wire. It is snapped around the neutral wire to sense the current flow. The module also requires connection to hot and neutral to measure the voltage being provided to the device. For Direct Current (DC) devices there is the PZEM-017 module.

![Figure 2: PZEM Wiring](https://github.com/BrucesHobbies/energyMaster/blob/main/figures/figure2.png)

# Required Hardware 
As an Amazon Associate I earn a small commission from qualifying purchases. It does not in any way change the prices on Amazon. I appreciate your support, if you purchase using the links below.

## PZEM Module (about $20 USD)
For Alternating Current (AC) devices
- One of the following AC power PZEM-016 modules - may have different shipping times
  - [Amazon: PZEM-016](https://amzn.to/394y8VT)
  - [Amazon: PZEM-016](https://amzn.to/2PhmK1M)
  - [Amazon: PZEM-016](https://amzn.to/3lG36su)

For Direct Current (DC) devices
- One of the following DC power PZEM-017 modules - may have different shipping times
  - [Amazon: PZEM-017](https://amzn.to/315rXwv)

2-conductor low voltage wire as needed (RS-485 connection from PZEM module to USB dongle)

## Raspberry Pi system (if you don’t already own one)
- Raspberry Pi (any of the following)
  - [RPI-Zero]( https://amzn.to/3ly0mM0)
  - [RPI 3B+]( https://amzn.to/3lyPBJe)
  - [RPI 4B]( https://amzn.to/2Vwulto)
- Power adapter for your Raspberry Pi
- Heatsinks (optional)
- SD-Card

# Software Installation
## Step 1: Setup the Raspberry Pi Operating System.
Here are the instructions to install the Raspberry Pi Operating System.
[Raspberry Software Install Procedure](https://www.raspberrypi.org/software/operating-systems/)

Before continuing make sure your operating system has been updated with the latest updates.

    sudo apt-get update
    sudo apt-get full-upgrade
    sudo reboot now

## Step 2: Download energyMaster software
To get a copy of the source files type in the following git command assuming you have already installed git:

    git clone https://github.com/BrucesHobbies/energyMaster

Download the prerequisite ModBus.

    sudo pip3 install pymodbus

Verify PZEM module presence using the RPi command line (once attached by USB cable and RS-485 cable with module power on):

    ls /dev/ttyUSB*    # Show USB devices
    lsusb -v           # Show USB devices with details

## Step 3: Configure energyMaster software (optional)
To add additional PZEM modules, add a name to the chanNames list in energyMaster.py. The example below is for four devices on separate USB dongles.

    chanNames = ["Device1","Device2","Device3","Device4"]
    chanPorts = ["/dev/ttyUSB0", "/dev/ttyUSB1", "/dev/ttyUSB2", "/dev/ttyUSB3"]   # One entry per chanName[]
    chanAddrs = [0x01, 0x01, 0x01, 0x01]                                           # One entry per chanName[]
    chanOnThresholds = [5, 20, 20, 20]                                 # Watts, with one entry per chanName[]


To change the sample interval or logging interval modify these lines.

    # Timing parameters
    tInterval = 0.5    # time interval in seconds between measuring current
                       # Nominal time on RPi3 is 0.072 seconds, don't go below 0.1 on RPi3 or Zero
    tLog = 15          # time interval in minutes between logging energy measurements to csv file

To disable or enable status messages and alerts modify these lines.

    statusMsgEnabled = 1                              # non zero enables sending of email / SMS text messages
    statusMsgHHMM    = [12, 0]                        # Status message time to send [hh, mm]

    alertMsgEnabled  = 1                              # non zero enables sending of email / SMS text messages
    runTimeAlert = [30*60] * len(chanNames)           # Run time to trigger email / SMS text - seconds
    minIntervalBtwEmails = [2*3600] * len(chanNames)  # Wait this long before sending another email - seconds

To update the device monitoring algorithm, see alg.py.


## Step 4: PubScribe Configuration (optional)
### Step 4a: Download database or publish/subscribe software such as MQTT (optional)

For example with MQTT:

    sudo apt-get install mosquitto             # local broker
    sudo apt-get install mosquitto-clients     # local publish-subscribe
    sudo systemctl enable mosquitto            # Enable the broker and allow it to auto-start after reboot
    sudo systemctl status mosquito             # Check status
    sudo pip3 install paho-mqtt                # Python interface to MQTT

### Step 4b: Edit pubScribe.py to reflect the options you would like to use (optional)

    #
    # USER CONFIGURATION SECTION
    # Select one or more options to enable
    #
    CSV_FILE_ENABLED  = 1
    EMAIL_SMS_ENABLED = 1
    MQTT_ENABLED      = 0
    INFLUX_DB_ENABLED = 0


## Step 5: Email Configuration (optional)
UPDATE: It has been reported that you don't actually need to lower the security settings for the RPi to access gmail. Gmail now allows you to set up a one-time password for low level security apps using gmail and still have TFA enabled. We still recommend a separate email account for your RPi for extra protection. 

You can use Google Gmail to send status and alert emails. Others have also used Microsoft Live/Outlook/Hotmail, Yahoo, Comcast, ATT, Verizon, and other email servers. 
Currently, status and alert messages are sent by email which can also be sent as an SMS text to your cell phone. Gmail works with Python on the Raspberry Pi if you set the Gmail security settings to low. As such, you can create a separate Gmail account to send messages from. Under your Gmail account settings you will need to make the following change to allow “Less secure app access”.

![Figure 3: Gmail Less Secure App Access](https://github.com/BrucesHobbies/energyMaster/blob/main/figures/figure3.png)


Then click on “Turn on access (not recommended)” by moving the slider to ON. Then click the back arrow.

![Figure 4: Enable Less Secure App Access]

(https://github.com/BrucesHobbies/energyMaster/blob/main/figures/figure4.png)


# Running The Program From A Terminal Window 
When your first email is sent at program startup, Google will ask you to confirm that it is you. You will need to sign into the device email account that you created and go to the critical security email that Google sent you and confirm you originated the email before Google will allow emails to be sent from your Python program.

Once you have created an account, start the energyMaster™ program.   Type:

    python3 energyMaster.py

The first time the program starts up it will ask you for your email user id and password for the account that you just created to work with this program. The password will be saved to a file called emailCfg.json.  Please be careful to not send that file to others. If you ever change your password you will need to delete emailCfg.json so that the program will ask you for your password again. 

    Enter sender’s device email userid (sending_userid@gmail.com):
    sending_userid@gmail.com

    Enter password:
    password

Next the program will ask you for the recipient email address.  This can either be the same email address, your primary email address or your SMS cell number carrier’s gateway.  To email an SMS to your cell phone construct the recipient email depending on your cell phone carrier:

Carrier|Format
-------|-------|
AT&T|number@txt.att.net|
Verizon|number@vtext.com|
Sprint PCS|number@messaging.sprintpcs.com|
T-Mobile|number@tmomail.net|
VirginMobile|number@vmobl.com|

    Enter recipient’s email userid (receiving_userid@something.com):
    receiving_userid@something.com
 

# Future Options
Please feel free to fork and contribute or provide feedback on priorities and features

# Feedback
Let us know what you think of this project and any suggestions for improvements. Feel free to contribute to this open source project.
