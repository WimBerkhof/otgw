#!/usr/bin/env python

from google.cloud import firestore
import google.cloud.exceptions
import urllib
import json
import sys
import subprocess
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
        with urllib.request.urlopen(os.environ["OTGWURL"]+"/json") as json_data:
            otgw_data = json.load(json_data)
    except IOError as e:
        print("I/O error({0}): {1}".format(e.errno, e.strerror))
        exit(1)
       
    # read weather data
    try:
        with open(os.environ["OUTTEMP"], 'r') as json_data:
            weather_data = json.load(json_data)
    except IOError as e:
        print("I/O error({0}): {1}".format(e.errno, e.strerror))
        exit(2)
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
    except IOError as e:
        print("I/O error({0}): {1}".format(e.errno, e.strerror))
        exit(2)
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
            u'boilertemp': float(otgw_data['boilertemp']['value']),
            u'chmode': parseBoolString(otgw_data['chmode']['value']),
            u'chwsetpoint': float(otgw_data['chwsetpoint']['value']),
            u'controlsp': float(otgw_data['controlsp']['value']),
            u'dhwenable': parseBoolString(otgw_data['dhwenable']['value']),
            u'dhwmode': parseBoolString(otgw_data['dhwmode']['value']),
            u'dhwsetpoint': float(otgw_data['dhwsetpoint']['value']),
            u'flame': parseBoolString(otgw_data['flame']['value']),
            u'maxmod': float(otgw_data['maxmod']['value']),
            u'modulation': float(otgw_data['modulation']['value']),
            u'outside': float(weather_data['main']['temp']),
            u'returntemp': float(otgw_data['returntemp']['value']),
            u'setpoint': float(otgw_data['setpoint']['value']),
            u'temperature': float(otgw_data['temperature']['value']),
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
        batch.set(zone_ref,{
                u'setpoint': float(evohome_data[i]['setpoint']),
		        u'temp': float(evohome_data[i]['temp']),
		        u'timestamp': firestore.SERVER_TIMESTAMP
	    })

    #
    # write documents
    #
    batch.commit()

if __name__ == '__main__':
    #os.system('bash -c \'source ~/.otsetcfg\.txt\'')
    subprocess.run("bash -c source ~/.otsetcfg.txt")
    run_quickstart()
    exit(0)