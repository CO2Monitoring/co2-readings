#!/usr/bin/python

import json
import datetime
import serial
import time
import sqlite3
import os

db_file = "/home/co2/readings.sqlite3"
#calibration_file = "/home/co2/.calibrated"
co2_sensor_port = "/dev/ttyAMA0"
pm_sensor_port = "/dev/ttyUSB0"

# Initializing CO2 sensor
def init_co2_sensor():
	global co2_sensor
	ser = serial.Serial(co2_sensor_port)
	ser.write("K 2\r\n") # Mode 2 - polling
	ser.flushInput()
	time.sleep(.01)
	ser.read(10)
	co2_sensor = ser

# Initializing PM2.5/0.5 sensor
def init_pm_sensor():
	global pm_sensor
	ser = serial.Serial(pm_sensor_port)

	# Setting up according to http://www.sylvane.com/media/documents/products/dc1100-com-port-option.pdf
	ser.baudrate = 9600
	ser.stopbits = 1
	ser.parity = 'N'
	ser.bytesize = 8
	# Disabling flow control
	ser.xonxoff = 0
	ser.rtsctf = 0
	ser.dsrdtr = 0
	ser.timeout = 125
	pm_sensor = ser


# CO2
def read_co2():
	co2_sensor.write("Z\r\n")
	time.sleep(.01)
	resp = co2_sensor.read(10)
	resp = resp[:8]
	try:
		fltCo2 = float(resp[2:])
	except ValueError,e:
		print "[Error] ", e
	return dict(value=str(fltCo2),unit="ppm")

# Temperature
def read_temp():
	co2_sensor.write("T\r\n")
	time.sleep(.01)
	resp = co2_sensor.read(10)
	resp = resp[:8]
	try:
		fltTemp = float(resp[5:])
		fltTemp /= 10
	except ValueError,e:
		print "[Error] ", e
	return dict(value=str(fltTemp),unit="degree Celsius")

# Humidity
def read_humidity():
	co2_sensor.write("H\r\n")
	time.sleep(.01)
	resp = co2_sensor.read(10)
	resp = resp[:8]
	try:
		fltHum = float(resp[5:])
		fltHum /= 10
	except ValueError,e:
		print "[Error] ",e
	return dict(value=str(fltHum),unit="percent")

def read_pm():
	pm_sensor.write("D\r\n")
	time.sleep(.01)
	pm_sensor.readline() # reading MIN
	readings = pm_sensor.readline() # reading last minute values
	
	# Reading all garbage too
	result = 1
	while result:
		result = pm_sensor.readline()
		if result.find("END")!=-1:
			pm_sensor.close()
			time.sleep(.01)
			break

	readings = readings.strip().split(",")
	pm05 = dict(value=readings[0],unit="counts/100 per cubic foot")
	pm25 = dict(value=readings[1],unit="counts/100 per cubic foot")
	return dict([("pm05", pm05), ("pm25", pm25)])

# def calibrate(port):
# 	ser = init_sensor(port)
# 	ser.write("G\r\n")
# 	ser.flushInput()
# 	time.sleep(.01)
# 	open(calibration_file, 'a').close()

def log(message):
	errorlog = open("error.log","a");
	errorlog.write(datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")+"# "+message+"\n")
	errorlog.close()

# Main execution
readings = {};
try: 
	init_co2_sensor()
	readings["co2"] = read_co2()
	readings["temperature"] = read_temp()
	readings["humidity"] = read_humidity()
except Exception as e:
	log("Couldn't work with CO2 sensor: "+str(e))

try: 
	init_pm_sensor()
	pm_readings = read_pm()
	readings["pm05"] = pm_readings["pm05"]
	readings["pm25"] = pm_readings["pm25"]
except Exception as e:
	log("Couldn't work with PM sensor: "+str(e)+"; characters in buffer: "+pm_sensor.inWaiting())
	log(pm_sensor.read(pm_sensor.inWaiting()))

# Producing JSON
#dthandler = lambda obj: obj.isoformat() if isinstance(obj, datetime.datetime) or isinstance(obj, datetime.date) else None
data = json.dumps({'readings': readings, 'timestamp': datetime.datetime.utcnow().isoformat()})

# Initializing DB
conn = sqlite3.connect(db_file)
c = conn.cursor()

c.execute("CREATE TABLE IF NOT EXISTS readings (data TEXT NOT NULL, created TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL, status INTEGER DEFAULT 0)")
c.execute("CREATE INDEX IF NOT EXISTS status ON readings (status)")
c.execute("CREATE INDEX IF NOT EXISTS created ON readings (created)")

# Inserting data
c.execute("INSERT INTO readings (`data`) VALUES (?)",(data,))
conn.commit()
conn.close()
