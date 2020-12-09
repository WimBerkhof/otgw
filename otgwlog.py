#!/usr/bin/env python

from google.cloud import firestore
import google.cloud.exceptions
from urllib.request import urlopen
from urllib.error import URLError
from urllib.error import HTTPError
import json
import sys
import os
import datetime

# true or false, return boolean
def parseBoolString(theString):
    return theString == "1"

# Raspberry Pi serial number (= OTGW identification)
def getserial():
  # Extract serial from cpuinfo file
  cpuserial = "0000000000000000"
  try:
    f = open('/proc/cpuinfo','r')
    for line in f:
      if line[0:6]=='Serial':
        cpuserial = line[10:26]
    f.close()
  except:
    cpuserial = "ERROR000000000"

  return cpuserial

def otgwDebug(*args):
    if os.environ["OTGWDEBUG"] == "1":
        logString = datetime.datetime.now().strftime("%c") + " :"
        for arg in args:
            logString += " " + str(arg)
        with open(os.environ["OTGWLOG"], "at") as f:
            f.write(logString + '\n')
    return

def otgwExit(exitValue):
    otgwDebug("otgwExit value = ", exitValue)
    sys.exit(exitValue)

def run_quickstart():

    getserial()
    #
    # get OTGW values in json format from the gateway
    #
    try:
        otgwDebug("read otgw vals")
        otgwData = json.loads(urlopen(os.environ["OTGWURL"] + "/json").read())
    except IOError as e:
        print("I/O error({0}): {1}".format(e.errno, e.strerror))
        otgwExit(1)

    # read weather data
    try:
        with open(os.environ["OUTTEMP"], 'r') as json_data:
            weather_data = json.load(json_data)
    except OSError as e:
            print("OS error({0}): {1}".format(e.errno, e.strerror))
            otgwExit(2)
    else:
        #print weather_data
        #print weather_data['main']['temp']
        json_data.close()

    #
    # get Evohome data in json format
    #
    try:
        with open (os.environ["EVOHOMEZ"], 'r') as json_data:
            evohome_data = []
            # one line per zone
            for evohome_zone in json_data:
                evohome_data.append(json.loads(evohome_zone))
    except OSError as e:
            print("OS error({0}): {1}".format(e.errno, e.strerror))
            otgwExit(3)
    else:
        json_data.close()

    #
    # Explicitly use service account credentials
    # by specifying the private key file.
    #
    db = firestore.Client.from_service_account_json(
        '/home/pi/.credentials/firestore-ThermoData.json')

    #
    # start batched write, several collections at once
    #
    batch = db.batch()

    #
    # create new collection OTGW data
    #
    otgwid = getserial()

    otgw_ref = db.collection(u'OTGW').document(otgwid).get()
    if otgw_ref is None:
            otgw_ref = db.collection(u'OTGW').document(otgwid).set({u'description': u'OpenTherm Gateway' })

    otgw_ref = db.collection(u'OTGW').document(otgwid).collection(u'samples').document()
    batch.set(otgw_ref, {
            u'boilertemp': float(otgwData['boilertemp']['value']),
            u'chmode': parseBoolString(otgwData['chmode']['value']),
            u'chwsetpoint': float(otgwData['chwsetpoint']['value']),
            u'controlsp': float(otgwData['controlsp']['value']),
            u'dhwenable': parseBoolString(otgwData['dhwenable']['value']),
            u'dhwmode': parseBoolString(otgwData['dhwmode']['value']),
            u'dhwsetpoint': float(otgwData['dhwsetpoint']['value']),
            u'flame': parseBoolString(otgwData['flame']['value']),
            u'maxmod': float(otgwData['maxmod']['value']),
            u'modulation': float(otgwData['modulation']['value']),
            u'outside': float(weather_data['main']['temp']),
            u'returntemp': float(otgwData['returntemp']['value']),
            u'setpoint': float(otgwData['setpoint']['value']),
            u'temperature': float(otgwData['temperature']['value']),
            u'timestamp': firestore.SERVER_TIMESTAMP
    })

    #
    # create collections for Evohome data
    #
    for i in range(0, len(evohome_data)):
        zone_ref = db.collection(u'evohome').document(evohome_data[i]['id']).get()
        if zone_ref is None:
                batch.set(zone_ref, {u'description': u'Evohome zone'})

        zone_ref = db.collection(u'evohome').document(evohome_data[i]['id']).collection(u'samples').document()
        batch.set(zone_ref, {
                u'setpoint': float(evohome_data[i]['setpoint']),
                u'temp': float(evohome_data[i]['temp']),
                u'timestamp': firestore.SERVER_TIMESTAMP
        })

    #
    # write documents
    #
    batch.commit()

if __name__ == '__main__':
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
