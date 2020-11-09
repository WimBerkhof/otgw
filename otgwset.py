#!/usr/bin/env python

import json
import math
import sys
import time
import datetime
import os
from urllib.request import urlopen
from urllib.error import URLError

def otgwCmd(otgwCommand, otgwParam):
    try:
        otgwResult = urlopen(os.environ["OTGWURL"] + "/command?" + otgwCommand + "=" + str(otgwParam)).read()
    except URLError as e:
        print("otgwCommand failed: " + e.reason)
        exit(99)
    else:
        return otgwResult

def otgwDebug(*args):
    if os.environ["OTGWDEBUG"] == "1":
        logString = datetime.datetime.now().strftime("%c") + " : "
        for arg in args:
            logString += str(arg)
        print(logString, file = sys.stderr)
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
        with open(os.environ["OTGWVALS"], "w") as f:
            json.dump(otgwData, f)
        if otgwData['dhwmode']['value'] == "1":
            # shower on, leave alone
            exit(0)

    # update wether data older than 19 minutes, restrict number of API calls
    if os.path.exists(os.environ["OUTTEMP"]) == False or (
        time.time() - os.path.getmtime(os.environ["OUTTEMP"])) > (19 * 60):
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
            with open(os.environ["OUTTEMP"], "w") as f:
                json.dump(weatherData, f)
            f.close()
    else:
        # read weather data
        with open(os.environ["OUTTEMP"], "r") as f:
            weatherData = json.load(f)

    # if changed more than 9 minutes (Evohome 6 switchpoints per hour)
    if os.path.exists(os.environ["EVOHOMEZ"]) == False or (
        time.time() - os.path.getmtime(os.environ["EVOHOMEZ"])) > (9 * 60):

        # load Evohome module
        sys.path.insert(0, os.environ["HOME"] + "/evohome-client")
        from evohomeclient2 import EvohomeClient

        # get Evohome zone temperature data
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
            with open(os.environ["EVOHOMEZ"], "w") as f:
                json.dump(evoWimm, f)
    else:
        with open(os.environ["EVOHOMEZ"], "r") as f:
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

    # outside temperature
    OT = float(weatherData['main']['temp'])

    if (MAXDIF > 0) and (HM == 1):
        # Evohome requests heating, set current setpoint

        # linear -20 > +20 outside temperature
        OTCSMIN = float(os.environ["OTCSMIN"])
        OTCSMAX = float(os.environ["OTCSMAX"])
        CS = OTCSMIN + 0.4 * (1 - OT / ((20 - -20)/2)) * (OTCSMAX - OTCSMIN) + MAXDIF

        # see cv manual
        pendelMax = 5

        PT = float(otgwData['boilertemp']['value'])
        if CS > PT + pendelMax:
            # gradual change
            CS = PT + pendelMax

        CS = math.ceil(CS)
        SH = (math.floor(CS / 5) + 1) * 5

        # maximum modulation (show override)
        MM = '79'

        # temporary setpoint
        TT = '0'
    else:
        # pass along thermostat value
        CS = 0

        # setpoint (just copy current)
        SH = float(otgwData['chwsetpoint']['value'])

        # reset override
        if otgwData['maxmod']['value'] == 79:
            MM = 'T'

        # lower temporary setpoint
        TT = '14'

    otgwDebug("CS= ", CS)
#
# 3. set central heating parameters
#
    # Evohome demand
    if MAXDIF > 0 and HM == 1:
        # wait until gateway mode
        while str(otgwCmd("PR", 'M')).find('M=M') > 0:
            otgwCmd("GW", '1')
            time.sleep(3)

        # outside (ambient) temperature
        if OT != otgwData["outside"]["value"]:
            otgwCmd("OT", OT)

        # set current setpoint
        otgwCmd("CS", CS)

        # set max. setpoint
        if SH != otgwData['chwsetpoint']['value']:
            otgwCmd("SH", SH)

        # (re)set maximum modulation
        otgwCmd("MM", MM)

        # (re)set temporary setpoint
        otgwCmd("TT", TT)
    else:
        # no Evohome demand
        while str(otgwCmd("PR", 'M')).find('M=M') < 0:
            # set OTGW to monitoring (if not already)
            otgwCmd("GW", '0')
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
