#!/usr/bin/python

# Flush script
# Run it weekly from cron

db_file = "/home/co2/readings.sqlite3"

import sqlite3

# Connecting to DB

try:
	conn = sqlite3.connect(db_file)
except Exception,e:
	print "Caught exception "+e
	exit()

c = conn.cursor()
c.execute("DELETE FROM readings WHERE status=2 AND created <= datetime('now','-7 days')") # Status=2 means "Synced"
conn.commit()
conn.close()
