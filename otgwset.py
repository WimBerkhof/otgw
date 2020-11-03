#!/usr/bin/env python3

from urllib.request import urlopen
import json
import sys
import time
import os


def run_quickstart():
    #
    # get OTGW values in json format from the gateway
    #
    try:
        otgw_data = json.loads(urlopen(os.environ["OTGWURL"] + "/json").read())
    except IOError as e:
        print("I/O error({0}): {1}".format(e.errno, e.strerror))
        exit(1)
    else:
        # success .. write otgw data
        with open("/tmp/otgwvals3.txt", "w") as f:
            json.dump(otgw_data, f)

    # data older than 19 minutes
    if os.path.exists("/tmp/outtemp3.txt") == False or (
        time.time() - os.path.getmtime("/tmp/outtemp3.txt")) > (19 * 60):
        weatherRequest = (os.environ["OTGWCITY"] + "&APPID=" + os.environ["APIKEYOT"] + "&units=metric")
        try:
            json_data = urlopen(
                "http://api.openweathermap.org/data/2.5/weather?q=" + weatherRequest).read()
        except OSError as e:
            print("I/O error({0}): {1}".format(e.errno, e.strerror))
            exit(2)
        else:
            # success .. write weather data
            weather_data = json.loads(json_data)
            with open("/tmp/outtemp3.txt", "w") as f:
                json.dump(weather_data, f)
            f.close()


if __name__ == "__main__":
    try:
        with open(os.environ["HOME"] + "/.otsetcfg.txt", "r") as f:
            for environVariable in f:
                if environVariable.find("export ", 0) != -1:
                    putenvLine = environVariable.replace("export ", "").split("=")
                    os.environ[putenvLine[0]] = putenvLine[1].rstrip("\n")
    except IOError as e:
        print("I/O error({0}): {1}".format(e.errno, e.strerror))
        exit(99)
    else:
        f.close()

    run_quickstart()
    exit(0)
