# OpenTherm Gateway (OTGW)

## Description

The OpenTherm Gateway (OTGW) is used to control and monitor the central heating. The heatpump didn't do as well as expected. By monitoring and subsequently lowering the requested temperatures the heatpump now does most of the work. Yeah !!

This project includes Python scripts to set and log central heating parameters. The plan is to only adjust setpoints when there is actual heating demand and not completely control central heating.

The current central heating setup is a Remeha 'Tzerra Hybrid 390 3C' system. Included are:  
- solar collectors;
- Mitsubishi Ecodan heatpump;
- Remeha Tzerra Plus central heating;
- Honeywell Evohome thermostat (with internet gateway, not wifi). 

The OTGW is connected via usb to a 'Raspberry Pi Model B+'

## References

- The OTGW site: http://otgw.tclcode.com/
- Evohome backend 'Total Connect Comfort': https://www.mytotalconnectcomfort.com
- The Evohome Python library: https://github.com/watchforstock/evohome-client
- OpenWeatherMap API: https://openweathermap.org/api

## otgwset.py

Python script which collects data about outside temperature and heating demand. 
The necessary setpoint ('CS') is calculated from a defined heating curve ("stooklijn").
Accordingly the maximum setpoint ('SH') is calculated to limit central heating temperature.

To override the thermostat the OTGW is run in gateway mode. When there's no heating demand (eg. at night) the control is transferred back to the thermostat, OTGW set to monitoring mode.

## otgwlog.py

Python script to log data to Google Firestore.

It's Python 2 only. Unable to fix all Google cloud dependencies on 'Raspberry Pi Model B+' (ARMv6) to migrate to Python 3.

Scheduled in cron to log data every two minutes:

        */2 * * * * python2 <full path>/otgwlog.py

## .otsetcfg.txt

Settings file for both Python scripts. Syntax: parameter=value

Parameter | Description
--------- | -----------
OTGWDEBUG | debug messages (0 or 1)
OTGWLOG | file path to log file
APIKEYOT | OpenWeatherMap API key
OTGWCITY | location of OTGW (for OpenWeatherMap)
OUTTEMP | file path to store weather data (eg. /tmp/outtemp.json)
EVOHOMEZ | file path to store Evohome zone data
EVOGATEWAY | ip-address of Evohome gateway (obsolete)
EVOLOGIN | Evohome backend portal login
EVOPASSWD | Evohome backend portal password
OTGWURL | url of OTGW gateway (eg. http://192.168.x.y:8080)
BUFTEMP | buffer temperature (when no heating demand)
OTCSMAX | heating curve setpoint -20 degrees celcius
OTCSMIN | heating curve setpoint +20 degrees celcius

## Installation

Install Python version 3 (currently using 3.9.0).
Copy the files to a directory.
Change permissions to executable: chmod 750 <file>

Run the script: python otgwset.py

Verify whether output files exist and contain valid data.

Schedule the script using cron. 
Align with number of switchpoints of thermostat, eg. six times per hour.

        1,11,21,31,41,51 * * * * <full path>/otgwset.py


## Todo list

- find out how to check whether Evohome data at backend portal is current;
- use TensorFlow to adjust heating curve based on history data in Google Firestore;
- create Javascript app/webpage to monitor central heating more advanced than 'otmonitor'.