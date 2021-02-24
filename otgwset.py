#!/usr/bin/env python3

import json
import math
import sys
import signal
import time
import datetime
import os
import requests
from urllib.request import urlopen
from urllib.error import HTTPError

#
# signal (eg. kill) handler
#
def handler(signal_received, frame):
    otgwDebug("signal received", signal_received)
    otgwExit(signal_received)

#
# send cmd to otgw
#
def otgwCmd(otgwCommand, otgwParam):
    otgwDebug("otgwCommand", otgwCommand, otgwParam)

    try:
        otgwResult = urlopen(os.environ["OTGWURL"] + "/command?" + otgwCommand + "=" + str(otgwParam)).read()
    except HTTPError as e:
        otgwDebug("otgwCommand failed: ", "code = ", e.code, " reason = ", e.reason)
        otgwExit(99)
    else:
        otgwDebug("otgwCommand succes, result =", otgwResult.decode("utf-8"))
        return otgwResult

#
# write debug line to logfile
#
def otgwDebug(*args):
    if os.environ["OTGWDEBUG"] == "1":
        logString = datetime.datetime.now().strftime("%c") + " :"
        for arg in args:
            logString += " " + str(arg)
        with open(os.environ["OTGWLOG"], "at") as f:
            f.write(logString + '\n')
            f.close()
    return

#
# exit python script, report value
#
def otgwExit(exitValue):
    otgwDebug("otgwExit value = ", exitValue)
#    if isinstance(exitValue, (int, str)) and exitValue != 0:
#        # failback to monitor mode
#        while str(otgwCmd("PR", 'M')).find('M=M') < 0:
#            # set OTGW to monitoring (if not already)
#            otgwCmd("GW", '0')
#            time.sleep(3)
    sys.exit(exitValue)

#
# main loop
#
def run_quickstart():
    otgwDebug("otgwset BEGIN")

    #
    # get OTGW values in json format from the gateway
    #
    try:
        otgwDebug("read otgw vals")
        otgwData = json.loads(urlopen(os.environ["OTGWURL"] + "/json").read())
    except HTTPError as e:
        otgwDebug("get otgwData failed: ", "code = ", e.code, " reason = ", e.reason)
    except IOError as e:
        print("I/O error({0}): {1}".format(e.errno, e.strerror))
        otgwExit(1)
    else:
        # success .. write otgw data
        with open(os.environ["OTGWVALS"], "w") as f:
            json.dump(otgwData, f)
            f.close()
        if otgwData['dhwmode']['value'] == "1":
            # shower on, leave alone
            otgwExit(2)

    otgwDebug("read weather data")

    # update wether data older than 17 minutes, restrict number of API calls
    if os.path.exists(os.environ["OUTTEMP"]) == False or (
        time.time() - os.path.getmtime(os.environ["OUTTEMP"])) > (17 * 60):
        weatherRequest = (os.environ["OTGWCITY"] + "&APPID=" + os.environ["APIKEYOT"] + "&units=metric")
        try:
            json_data = urlopen(
                "http://api.openweathermap.org/data/2.5/weather?q=" + weatherRequest).read()
        except HTTPError as e:
            otgwDebug("get weatherData failed: ", "code = ", e.code, " reason = ", e.reason)
        except OSError as e:
            print("OS error({0}): {1}".format(e.errno, e.strerror))
            otgwExit(3)
        else:
            # success .. write weather data
            otgwDebug("write weather data")
            weatherData = json.loads(json_data)
            with open(os.environ["OUTTEMP"], "w") as f:
                json.dump(weatherData, f)
                f.close()
    else:
        # read weather data
        with open(os.environ["OUTTEMP"], "r") as f:
            weatherData = json.load(f)
            f.close()

    # reply timeout Evohome backend portal
    TCCTimeout = 113

    # if changed more than 5 minutes (Evohome 6 switchpoints per hour)
    if os.path.exists(os.environ["EVOHOMEZ"]) == False or (
        time.time() - os.path.getmtime(os.environ["EVOHOMEZ"])) > (9 * 60 - 2 * TCCTimeout):

        # load Evohome module
        sys.path.insert(0, os.environ["HOME"] + "/evohome-client")
        from evohomeclient2 import EvohomeClient

        # get Evohome zone temperature data
        try:
            otgwDebug("retrieve Evohome data")

            #login to Evohome backend
            evoClient = EvohomeClient(os.environ["EVOLOGIN"], os.environ["EVOPASSWD"], debug=False, timeout=TCCTimeout)
        except (requests.HTTPError, requests.Timeout, Exception) as e:
        # except (requests.HTTPError, requests.Timeout) as e:
            otgwDebug("EvohomeClient error: ", str(e))

            # in case of error assume no demand
            evoWimm = [{ "id": "999999999", "name": "EvohomeERR", "temp": 99.0, "setpoint": 99.0}]
        else:
            # succes .. write Evohome data
            otgwDebug("Evohome TCC connected")
            evoWimm = []
            for evoData in evoClient.temperatures():
                evoWimm.append(evoData)

        if len(evoWimm) <= 0:
            otgwDebug("Evohome data, no zones")
            otgwExit(33)
        else:
            otgwDebug("write Evohome data, zones: ", len(evoWimm))
            with open(os.environ["EVOHOMEZ"], "w") as f:
                json.dump(evoWimm, f)
                f.close()

    otgwDebug("read Evohome data")
    with open(os.environ["EVOHOMEZ"], "r") as f:
        evoWimm = json.load(f)
        f.close()

#
# 2. calculate central heating settings
#
    i = 0 # zones request
    y = 0 # zones over setpoint
    totalDiff = 0
    for evoZone in evoWimm:
        zoneDiff = evoZone['setpoint'] - evoZone['temp']
        otgwDebug("evoData zone", evoZone['name'], "dif =", zoneDiff)
        if zoneDiff > 0:
            totalDiff = totalDiff + zoneDiff
            i = i + 1
        if zoneDiff < 0:
            y = y + 1

    # average heating demand
    otgwDebug("totallDiff =", totalDiff, ", i =", i)
    if i > 0:
        # some zones request heat
        AVGDIF = totalDiff / i
    else:
        if (y == 0):
            # all zones at setpoint
            AVGDIF = 0
        else:
            # all zones over setpoint
            AVGDIF = -1

    # heating mode
    HM = int(otgwData['chmode']['value'])

    # outside temperature
    OT = float(weatherData['main']['temp'])

    if (AVGDIF > 0) and (HM == 1):
        # Evohome requests heating, set current setpoint

        # min/max values of heating curve
        OTCSMIN = float(os.environ["OTCSMIN"])
        OTCSMAX = float(os.environ["OTCSMAX"])

        # linear -20 > +20 outside temperature
        CS = OTCSMIN + AVGDIF + ((20 - OT)/(20 - -20)) * (OTCSMAX - OTCSMIN)

        otgwDebug("CS heating curve = ", CS)

        # see cv manual
        pendelMax = 15

        PT = float(otgwData['boilertemp']['value'])
        if CS > PT + pendelMax:
            # gradual change at start
            otgwDebug("pendelmax", pendelMax, "active")
            CS = PT + pendelMax

        CS = math.ceil(CS)
        SH = (math.floor(CS / 5) + 1) * 5

        # maximum modulation (show override)
        MM = '99'

        # temporary setpoint
        TT = '0'
    else:
        # pass along thermostat value
        CS = 0

        # 'buffer bottom' temperature
        SH = float(os.environ["BUFTEMP"])
        #SH = float(otgwData['chwsetpoint']['value'])

        # reset override
        MM = '93'

        # lower temporary setpoint
        TT = '17'

    #
    # 3. set central heating parameters
    #
    otgwDebug("AVGDIF =", AVGDIF, "HM =", HM)
    otgwDebug("CS =", CS, "returntemp =", otgwData['returntemp']['value'],"SH =", SH)

    # Evohome demand                return hotter than setpoint
    if (HM == 1) and ((AVGDIF >= 0) or (float(otgwData['returntemp']['value']) > SH)):
        # wait until gateway mode
        while str(otgwCmd("PR", 'M')).find('M=M') > 0:
            otgwCmd("GW", '1')
            time.sleep(3)

        # outside (ambient) temperature
        try:
            type(otgwData["outside"]["value"])
        except:
            # doesn't exist yet
            otgwCmd("OT", OT)
        else:
            # set OT if different
            if OT != float(otgwData["outside"]["value"]):
                otgwCmd("OT", OT)

        if (float(otgwData['chwsetpoint']['value']) != float(os.environ["BUFTEMP"])) or (SH != float(os.environ["BUFTEMP"])):
            # set current setpoint
            otgwCmd("CS", CS)

            # (re)set maximum modulation
            otgwCmd("MM", MM)

        # (re)set temporary setpoint
        otgwCmd("TT", TT)

        # set max. setpoint
        if SH != float(otgwData['chwsetpoint']['value']):
            otgwCmd("SH", SH)
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
    # catch timeout (default TERM)
    signal.signal(signal.SIGTERM, handler)

    # other kill signals
    if (signal.SIGHUP):
        # Linux only
        signal.signal(signal.SIGHUP, handler)
    signal.signal(signal.SIGINT, handler)

    try:
        with open(os.environ["HOME"] + "/.otsetcfg.txt", "r") as f:
            for environVariable in f:
                if environVariable.find("export ", 0) != -1:
                    putenvLine = environVariable.replace("export ", "").split("=")
                    os.environ[putenvLine[0]] = putenvLine[1].rstrip("\n")
        f.close()
    except IOError as e:
        print("I/O error({0}): {1}".format(e.errno, e.strerror))
        otgwExit(11)

    # redirect stderr
    sys.stderr = open(os.environ["OTGWLOG"], "at")

    # Python search path
    otgwDebug(sys.path)
    #for module in sys.modules:
    #    otgwDebug(sys.modules[module])

    try:
        run_quickstart()
    except Exception as e:
        # failback to monitor mode
        otgwDebug("otgwset ERROR = ", e)
        otgwExit(e)
    else:
        otgwExit(0)
    finally:
        otgwDebug("otgwset EXIT")