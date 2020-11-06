#!/usr/bin/env python3

import json
import math
import sys
import time
import os
from urllib.request import urlopen
from urllib.error import URLError


def otgwcmd(otgwCommand, otgwParam):
    try:
        otgwResult = urlopen(os.environ["OTGWURL"] + "/command?" + otgwCommand + "=" + str(otgwParam)).read()
    except URLError as e:
        print("otgwCommand failed: " + e.reason)
        exit(99)
    else:
        return otgwResult

def otgwdebug(logString):
    if os.environ["OTGWDEBUG"] == "1":
        print(str(logString), file = sys.stderr)
    return

def run_quickstart():
    #
    # get OTGW values in json format from the gateway
    #
    try:
        otgwData = json.loads(urlopen(os.environ["OTGWURL"] + "/json").read())
    except IOError as e:
        print("I/O error({0}): {1}".format(e.errno, e.strerror))
        exit(1)
    else:
        # success .. write otgw data
        with open("/tmp/otgwvals3.txt", "w") as f:
            json.dump(otgwData, f)
        if otgwData['dhwmode']['value'] == "1":
            # shower on, leave alone
            exit(0)

    # update wether data older than 19 minutes
    if os.path.exists("/tmp/outtemp3.txt") == False or (
        time.time() - os.path.getmtime("/tmp/outtemp3.txt")) > (19 * 60):
        weatherRequest = (os.environ["OTGWCITY"] + "&APPID=" + os.environ["APIKEYOT"] + "&units=metric")
        try:
            json_data = urlopen(
                "http://api.openweathermap.org/data/2.5/weather?q=" + weatherRequest).read()
        except OSError as e:
            print("OS error({0}): {1}".format(e.errno, e.strerror))
            exit(2)
        else:
            # success .. write weather data
            weatherData = json.loads(json_data)
            with open("/tmp/outtemp3.txt", "w") as f:
                json.dump(weatherData, f)
            f.close()
    else:
        with open("/tmp/outtemp3.txt", "r") as f:
            weatherData = json.load(f)

    if os.path.exists("/tmp/evohomez3.txt") == False or (
        time.time() - os.path.getmtime("/tmp/evohomez3.txt")) > (9 * 60):
        # get Evohome zone data
        sys.path.insert(0, os.environ["HOME"] + "/evohome-client")
        from evohomeclient2 import EvohomeClient

        try:
            #login to Evohome backend
            evoClient = EvohomeClient(os.environ["EVOLOGIN"], os.environ["EVOPASSWD"])
        except OSError as e:
            print("OS error({0}): {1}".format(e.errno, e.strerror))
            exit(3)
        else:
            # succes .. get Evohome data
            evoWimm = []
            for evoData in evoClient.temperatures():
                evoWimm.append(evoData)
            with open("/tmp/evohomez3.txt", "w") as f:
                json.dump(evoWimm, f)
    else:
        with open("/tmp/evohomez3.txt", "r") as f:
            evoWimm = json.load(f)

#
# 2. calculate central heating settings
#
    MAXDIF = -1
    for evoZone in evoWimm:
        zoneDiff = evoZone['setpoint'] - evoZone['temp']
        if zoneDiff > MAXDIF:
            MAXDIF = zoneDiff
    if MAXDIF > 5:
        MAXDIF = 5

    # heating mode
    HM = int(otgwData['chmode']['value'])

    # setpoint
    SP = float(otgwData['chwsetpoint']['value'])
    SH = float(otgwData['chwsetpoint']['value'])

    # outside temperature
    OT = float(weatherData['main']['temp'])

    if (MAXDIF > 0) and (HM == 1):
        # Evohome requests heating, set current setpoint

        # linear -20 > +20 outside temperature
        OTCSMIN = float(os.environ["OTCSMIN"])
        OTCSMAX = float(os.environ["OTCSMAX"])
        CS = OTCSMIN + 0.4 * (1 - OT / 20) * (OTCSMAX - OTCSMIN) + MAXDIF

        # see cv manual
        pendelMax = 5

        PT = float(otgwData['boilertemp']['value'])
        if CS > PT + pendelMax:
            CS = PT + pendelMax

        CS = math.ceil(CS)
        SH = (math.floor(CS / 5) + 1) * 5

        # maximum modulation (show override)
        MM = '79'

        # temporary setpoint
        TT = '0'
    else:
        print("else", MAXDIF, HM, sep = ' | ')
        # pass along thermostat value
        CS = 0

        if otgwData['maxmod']['value'] == 79:
            MM = 'T'

        # lower temporary setpoint
        TT = '14'

#
# 3. set central heating parameters
#
    if MAXDIF >= 0 and HM == 1:
        # wait until gateway mode
        while str(otgwcmd("PR", 'M')).find('M=M') > 0:
            otgwcmd("GW", '1')
            time.sleep(3)

        # outside (ambiant) temperature
        if OT != otgwData["outside"]["value"]:
            otgwcmd("OT", OT)

        # set current setpoint
        otgwcmd("CS=", CS)

        if SP != SH:
            otgwcmd("SH", SH)

        # (re)set temporary setpoint
        otgwcmd("TT", TT)
    else:
        # no heating demand
        while str(otgwcmd("PR", 'M')).find('M=M') < 0:
            # set OTGW to monitoring (if not already)
            otgwcmd("GW", '0')
            time.sleep(3)

#
# Main
#
if __name__ == "__main__":
    try:
        with open(os.environ["HOME"] + "/.otsetcfg.txt", "r") as f:
            for environVariable in f:
                if environVariable.find("export ", 0) != -1:
                    putenvLine = environVariable.replace("export ", "").split("=")
                    os.environ[putenvLine[0]] = putenvLine[1].rstrip("\n")
    except IOError as e:
        print("I/O error({0}): {1}".format(e.errno, e.strerror))
        exit(11)
    else:
        f.close()

    run_quickstart()
    exit(0)