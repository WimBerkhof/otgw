
#!/usr/bin/env python2

from google.cloud import firestore
import google.cloud.exceptions
import urllib2
import json
import sys
import os

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

def run_quickstart():

    getserial()

    #
    # get OTGW values in json format from the gateway
    #
    try:
        otgwData = json.loads(urllib2.urlopen(os.environ["OTGWURL"]+"/json").read())
    except IOError as e:
        print("I/O error({0}): {1}".format(e.errno, e.strerror))
        exit(1)

    # read weather data
    try:
        with open(os.environ["OUTTEMP"], 'r') as f:
            weatherData = json.load(f)
            f.close
    except IOError as e:
        print("I/O error({0}): {1}".format(e.errno, e.strerror))
        exit(2)
    #else:
        #print weatherData
        #print weatherData['main']['temp']

    #
    # get Evohome data in json format
    #
    try:
        evohomeData = []
        with open (os.environ["EVOHOMEZ"], 'r') as f:
            evohomeData = json.load(f)
            f.close()
    except IOError as e:
        print("I/O error({0}): {1}".format(e.errno, e.strerror))
        exit(2)

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

    otgw_ref = db.collection('OTGW').document(otgwid).get()
    if otgw_ref is None:
            otgw_ref = db.collection('OTGW').document(otgwid).set({'description': 'OpenTherm Gateway' })

    otgw_ref = db.collection('OTGW').document(otgwid).collection('samples').document()
    batch.set(otgw_ref, {
            'boilertemp': float(otgwData['boilertemp']['value']),
            'chmode': parseBoolString(otgwData['chmode']['value']),
            'chwsetpoint': float(otgwData['chwsetpoint']['value']),
            'controlsp': float(otgwData['controlsp']['value']),
            'dhwenable': parseBoolString(otgwData['dhwenable']['value']),
            'dhwmode': parseBoolString(otgwData['dhwmode']['value']),
            'dhwsetpoint': float(otgwData['dhwsetpoint']['value']),
            'flame': parseBoolString(otgwData['flame']['value']),
            'maxmod': float(otgwData['maxmod']['value']),
            'modulation': float(otgwData['modulation']['value']),
            'outside': float(weatherData['main']['temp']),
            'returntemp': float(otgwData['returntemp']['value']),
            'setpoint': float(otgwData['setpoint']['value']),
            'temperature': float(otgwData['temperature']['value']),
            'timestamp': firestore.SERVER_TIMESTAMP
    })

    #
    # create collections for Evohome data
    #
    for i in range(0, len(evohomeData)):
        zone_ref = db.collection('evohome').document(evohomeData[i]['id']).get()
        if zone_ref is None:
                batch.set(zone_ref, {'description': 'Evohome zone'})

        zone_ref = db.collection('evohome').document(evohomeData[i]['id']).collection('samples').document()
        batch.set(zone_ref, {
                'setpoint': float(evohomeData[i]['setpoint']),
                'temp': float(evohomeData[i]['temp']),
                'timestamp': firestore.SERVER_TIMESTAMP
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
