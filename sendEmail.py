#!/usr/bin/env python

"""
Copyright(C) 2021, BrucesHobbies
All Rights Reserved

AUTHOR: Bruce
DATE: 12/08/2020
REVISION HISTORY
  DATE        AUTHOR          CHANGES
  yyyy/mm/dd  --------------- -----------------------------------------
  2021/01/25  BrucesHobbies   Added #!, moved imports to after comments
  2021/03/01  BrucesHobbies   Included cfgData.py
                              Removed key from cfg.json
                              Changed key generation

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

GENERAL INFO
  gmail email account security setting must be set to low!
    gmail password can only contain a-z, A-Z, and 0-9. No special characters.

  To send a text message to your phone, use one of the following email addresses 
      depending for your carrier:
  AT&T:		number@txt.att.net
  Sprint PCS: 	number@messaging.sprintpcs.com
  T-Mobile: 	number@tmomail.net
  Verizon: 	number@vtext.com
  VirginMobile:	number@vmobl.com

  SMTP server domain names:
  smtp.gmail.com (port 587 TLS)
  smtp-mail.outlook.com (port 587 TLS)
  smtp.live.com (port 587 TLS)		# alias for Outlook/Hotmail
  smtp.mail.yahoo.com
  smtp.comcast.net
  smtp.mail.att.net (port 465 SSL)
  smtp.verizon.net (port 465 SSL)
"""

import subprocess
import time
import smtplib
from cryptography.fernet import Fernet
import base64

try:
    import json
except ImportError:
    try:
        import simplejson as json
    except ImportError:
        print("Error: import json module failed")
        sys.exit()

encoding = 'utf-8'


#
# Email server configuration
#

SMTPSERVERTLSPORT = 'smtp.gmail.com:587'

# SMTPSERVER = 'smtp.gmail.com'
# SMTPTLSPORT = 587                   # For TLS, newer than SSL
# SMTPSSLPORT = 465                   # For SSL


FROM_USERID   = 'FROM_USERID'
STATUS_USERID = 'STATUS_USERID'
ALERT_USERID  = 'ALERT_USERID'


#
# --- Send text message ---
#
def send_mail(to_UserID_key, subj, msg) : 

    from_UserID = cfgData[FROM_USERID]
    passwd = password_decrypt(cfgData['token'])
    to_UserID = cfgData[to_UserID_key]

    print("Sending email on " + time.strftime("%a, %d %b %Y %H:%M:%S \n", time.localtime()))

    fullMsg = 'To: ' + to_UserID + '\nFrom: ' + from_UserID + '\nSubject: ' + subj + '\n\n' + msg + '\n\n'
    print(fullMsg)


    if (from_UserID!="") and (passwd!="") and (to_UserID!="") :
        try:
            server = smtplib.SMTP(SMTPSERVERTLSPORT)
            server.starttls()
            server.login(from_UserID, passwd)
            server.sendmail(from_UserID, to_UserID, fullMsg)
            
            """ SSL alternative instead of TLS...
            context = ssl.create_default_context()
            with smtplib.SMTP_SSL(SMTPSERVER, SMTPSSLPORT, context=context) as server:
                server.login(from_UserID, passwd)
                server.sendmail(from_UserID, to_UserID, fullMsg)
            """

            print("--- End of message ---")

        except Exception as e:
            print(e)

        finally:
            server.quit()    # TLS quit

    else :
        print("No userids and a password - local message only!\n")




cfgData = {
    u"token": "",
    u"FROM_USERID": "",
    u"ALERT_USERID": "",
    u"STATUS_USERID": ""
}


fernetKey = []


def password_key() :
     global fernetKey
     keyGen = bytes(subprocess.getoutput('cat /etc/machine-id'),'UTF-8')
     fernetKey = Fernet(base64.urlsafe_b64encode(keyGen))


def password_encrypt(phrase) :
    token = fernetKey.encrypt(bytes(phrase,encoding))
    return token.decode(encoding)


def password_decrypt(token) :
    phrase = fernetKey.decrypt(bytes(token,encoding))
    return phrase.decode(encoding)


def loadJsonFile(cfgDataFileName = 'emailCfg.json') :
    global cfgData

    password_key()

    try:
        with open(cfgDataFileName, 'r') as cfgDataFile:
            cfgData_temp = json.load(cfgDataFile)
            for key in cfgData:  # If file loaded, replace default values in cfgData with values from file
                if key in cfgData_temp:
                   cfgData[key] = cfgData_temp[key]

    # If file does not exist, it will be created using defaults.
    except IOError:  
        print("Enter sender's device email userid (sending_userid@gmail.com):")    # Sender's email userid
        cfgData[FROM_USERID] = input()

        print("Enter password: ")
        cfgData['token'] = password_encrypt(input())

        print("Enter recipient's email userid (recipient_userid@something.com) for alerts:")  # Recepient's email userid
        cfgData[ALERT_USERID] = input()

        print("Enter recipient's email userid (recipient_userid@something.com) for status:")  # Recepient's email userid
        cfgData[STATUS_USERID] = input()

        with open(cfgDataFileName, 'w') as cfgDataFile:
            json.dump(cfgData, cfgDataFile)

    return


#
# Test and debug
#
if __name__ == '__main__' :

    loadJsonFile('emailCfg.json')
    print("")
    print("TOKEN         : " + cfgData['token'])
    print("")
    print("USERID        : " + cfgData[FROM_USERID])
    print("PW            : " + password_decrypt(cfgData['token']))
    print("ALERT_USERID  : " + cfgData['ALERT_USERID'])
    print("STATUS_USERID : " + cfgData[STATUS_USERID])

    SUBJECT = 'Subj of Status'
    MSG = 'Status Message.'
    send_mail(STATUS_USERID, SUBJECT, MSG)

    SUBJECT = 'Subj of Alert!'
    MSG = 'Alert Message!'
    send_mail(ALERT_USERID, SUBJECT, MSG)

