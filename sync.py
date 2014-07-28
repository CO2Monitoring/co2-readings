#!/usr/bin/python

# Syncronization script

import hashlib
from hmac import new as hmac
import urllib2
import os
import stat
import sqlite3

# Settings
domain = "http://co2.example.com"
deviceid_file = "/home/co2/etc/deviceid"
devicekey_file = "/home/co2/etc/devicekey"
db_file = "/home/co2/readings.sqlite3"


# Reading device ID
try:
        f = open(deviceid_file,'r')
        device_id = f.readline().strip()
        f.close()
except IOError:
        exit("Can't open "+deviceid_file)

# Checking secret key file permissions
st = os.stat(devicekey_file)
if bool(st.st_mode & stat.S_IRGRP):
        print "[ERROR] File containing device secret key ("+devicekey_file+") is group readable. Run chmod 600 /etc/co2/devicekey",
        exit()

if bool(st.st_mode & stat.S_IROTH):
        print "[ERROR] File containing device secret key ("+devicekey_file+") is readable by anyone. Run chmod 600 /etc/co2/devicekey",
        exit()


# Reading device secret key
try:
        f = open(devicekey_file,'r')
        device_key = f.readline().strip()
        f.close()
except IOError:
        exit("[ERROR] Can't open file containing device secret key ("+devicekey_file+")")


# Connecting to DB

try:
	conn = sqlite3.connect(db_file)
except Exception,e:
	print "Caught exception "+e
	exit()

c = conn.cursor()

# Fetching data
c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='readings'")
if c.fetchone()==None:
	conn.close()
	exit("No readings yet")

c.execute("UPDATE readings SET status=1 WHERE status=0")

data = []
ids = []
for row in c.execute("SELECT rowid,data FROM readings WHERE status=1 LIMIT 100"):
	ids.append(row[0])
	data.append(row[1])

if len(data)==0:
	conn.close()
	exit("No data yet, exiting.")


data = ', '.join(data)

requestBody = '{"device_id": "'+device_id+'", "uri": "/readings", "data": ['+data+']}'

# Signing data
signature = hmac(device_key, requestBody, hashlib.sha256).digest().encode('base64').strip()

# Sending POST request to /readings

# DEBUG
handler=urllib2.HTTPHandler(debuglevel=1)
opener = urllib2.build_opener(handler)
urllib2.install_opener(opener)

req = urllib2.Request(domain+"/readings")
req.add_header('Authorization','HMAC '+signature)
req.add_header('Accept','application/json')
req.add_header('Content-Type','application/json')
try:
    res = urllib2.urlopen(req,requestBody)
    if res.getcode()==200:
    	c.execute("UPDATE readings SET status=2 WHERE rowid IN ("+', '.join(str(id) for id in ids)+")") # This is NOT a SQL injection
    	conn.commit()
except urllib2.HTTPError as e:
        # TODO ??
        print "HTTP error[{0}] {1}".format(e.errno, e.strerror)

conn.close()
