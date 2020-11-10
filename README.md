# OpenTherm Gateway (OTGW)

## Description

The OpenTherm Gateway (OTGW) is used to control and monitor the central heating. The heatpump didn't do as well as expected. By monitoring and subsequently lowering the requested temperatures the heatpump now does most of the work. Yeah !!

This project includes Python scripts to set and log central heating parameters. The plan is to only adjust setpoints and not completely control central heating.

The current central heating setup is a Remeha 'Tzerra Hybrid 390 3C' system. Included are:  
- solar collectors;
- a Mitsubishi Ecodan heatpump;
- Remeha Tzerra central heating;
- Honeywell Evohome thermostat (with internet gateway, not wifi). 

The OTGW is connected via usb to a 'Raspberry Pi Model B+'

## References

- The OTGW site: http://otgw.tclcode.com/
- The Evohome Python library: https://github.com/watchforstock/evohome-client
- OpenWeatherMap API: https://openweathermap.org/api

## otgwset.py

Python script which collects data about outside temperature and heating demand. 
The necessary setpoint ('CS') is calculated from a defined heating curve ("stooklijn").

When there's no heating demand the control is transferred back to the Evohome again, OTGW set to monitoring.

The otgwset.py runs every ten minutes by cron. The Evohome interval is six times per hour.

## otgwlog.py

Python script to log data to Google Firestore.

## .otsetcfg.txt

Settings file for both Python scripts. Syntax: parameter=value

Parameter | Description
--------- | -----------
OTGWDEBUG | debug messages (0 or 1)
APIKEYOT | OpenWeatherMap API key
OTGWCITY | location of OTGW (for OpenWeatherMap)
OUTTEMP | file path to store weather data (eg. /tmp/outtemp.txt)
EVOHOMEZ | file path to store Evohome zone data
EVOGATEWAY | ip-address of Evohome gateway
EVOLOGIN | Evohome login
EVOPASSWD | Evohome password
OTGWURL | url of OTGW gateway (eg. http://192.168.x.y:8080)
OTCSMAX | heating curve setpoint -20 degrees celcius
OTCSMIN | heating curve setpoint +20 degrees celcius

## Installation

Copy the files to a directory.
Change permissions to executable: chmod 750 <file>

## Todo list

- use TensorFlow to adjust heating curve based on history data in Google Firestore
- create Javascript app/webpage to monitor central heating more advanced than 'otmonitor'
