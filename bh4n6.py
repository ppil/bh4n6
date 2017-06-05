#!/usr/bin/python
# Browser history extraction
# Peter Pilarski

import os
import sys
import csv
import glob
import pyesedb
import sqlite3
import datetime
from urlparse import urlparse
from getopt import getopt, GetoptError

version = 1.1 # Windows volumes only

def usage():
	print """Browser history extraction v%s

Usage: %s --mount <mount_dir>


Options:
-m, --mount <mount_dir>
	Mount point of evidentiary volume
-o, --output <output_file>
	Where to store this script's output
	Default: ./browser_history.txt
-s, --search <term>
	Only pay attention to URLs that contain this string
-c, --chrome
	Handle Google Chrome browsing history
-f, --firefox
	Handle Mozilla Firefox browsing history
-i --ie
	Handle Microsoft IE10+ and Edge browsing history
"""%(version, sys.argv[0])

def read_args():
	# Initialize, set defaults
	cfg={}
	cfg["mount_dir"] = ""
	cfg["out_file"] = "%s/browser_history.txt"%os.getcwd()
	cfg["search"] = ""
	cfg["all"] = 1
	cfg["firefox"] = 0
	cfg["chrome"] = 0
	cfg["ie"] = 0
	try:
		opts, args = getopt(sys.argv[1:], 'fcim:s:o:', ["mount=","search=","output=","firefox","chrome","ie"])
	except GetoptError as err:
		sys.stdout.write(str(err))
		usage() # RTFM
		sys.exit(2)
	for o, a in opts: # option, argument
		if o in ("-m", "--mount"):
			cfg["mount_dir"] = a
		elif o in ("-s", "--search"):
			cfg["search"] = a
		elif o in ("-o", "--output"):
			cfg["out_file"] = a
		elif o in ("-f", "--firefox"):
			cfg["all"] = 0
			cfg["firefox"] = 1
		elif o in ("-c", "--chrome"):
			cfg["all"] = 0
			cfg["chrome"] = 1
		elif o in ("-i", "--ie"):
			cfg["all"] = 0
			cfg["ie"] = 1
	# Don't trust user input
	if os.path.isdir(cfg["mount_dir"]):
		cfg["mount_dir"] = os.path.abspath(cfg["mount_dir"])
	else:
		print "Invalid mount directory"
		sys.exit(1)
	return cfg

# Find databases using pattern expansion
def find_dbs(path):
	dbs = []
	for db in glob.glob(path):
		if os.path.isfile(db):
			dbs.append(db)
	return dbs

# Tread carefully, my friend
def query_sqlite(db,query):
	rows = 0
	try:
		conn = sqlite3.connect(db)
	except Exception as ex:
		print "Failed to open %s (%s)"%(db,ex)
		return
	rows = conn.execute(query)
	try:
		rows = conn.execute(query)
	except Exception as ex:
		print "Failed to query %s (%s)"%(db,ex)
		return
	return rows

# Get username from an appdata path
def user_of(path):
	start = path.find("Users")+6
	end = path.find("AppData")-1
	return path[start:end]

# Find and parse ESE databases for IE/Edge
def ie_hist(cfg):
	csv_list = []
	dbs = find_dbs(os.path.join(cfg["mount_dir"],"Users",'*',"AppData","Local","Microsoft","Windows","WebCache","WebCacheV??.dat"))
	for db in dbs:
		user = user_of(db)
		history_containers = []
		db_fh = open(db, 'rb')
		ese_db = pyesedb.file()
		ese_db.open_file_object(db_fh)
		containers = ese_db.get_table_by_name("Containers")
		if not containers:
			print "Error opening Containers table in %s"%db
			break
		# Find history tables from the Containers table
		for row in range(0,containers.get_number_of_records()-1):
			container = containers.get_record(row)
			row_id = str(container.get_value_data_as_integer(0))
			row_name = container.get_value_data_as_string(8)
			row_dir = container.get_value_data_as_string(10)
			if "History" in row_name and ("History.IE5" in row_dir or "MicrosoftEdge" in row_dir):
				history_containers.append(row_id)
		# Parse each history table/container
		for i in history_containers:
			current_table = ese_db.get_table_by_name("Container_%s"%i)
			if not current_table:
				print "Error opening table Container_%s in %s"%(i,db)
				continue
			# For each row
			for row_num in range(0,current_table.get_number_of_records()-1):
				row = current_table.get_record(row_num)
				if not row:
					break
				# Handle long values in the URL column
				if row.is_long_value(17):
					url = row.get_value_data_as_long_value(17).get_data_as_string()
				else:
					url = row.get_value_data_as_string(17)
				# Account for search parameters
				if cfg["search"] and cfg["search"] not in url:
					continue
				# Normalize data, add to CSV buffer
				url = '@'.join(url.split('@')[1:])
				accessed_time = row.get_value_data_as_integer(13)
				timestamp = datetime.datetime(1602,1,1)+datetime.timedelta(microseconds=(accessed_time/10))
				# Append time, domain, title (unavailable), url, browser, user
				csv_list.append([str(timestamp), urlparse(url).hostname, None, url, "IE/Edge", user])
		ese_db.close()
	write_lines(cfg["out_file"], csv_list)

# Find and parse SQLite databases for Firefox	
def firefox_hist(cfg):
	csv_list = []
	dbs = find_dbs(os.path.join(cfg["mount_dir"],"Users",'*',"AppData","Roaming","Mozilla","Firefox","Profiles",'*',"places.sqlite"))
	query = "SELECT moz_historyvisits.visit_date, moz_places.url, moz_places.title, moz_places.rev_host FROM moz_places, moz_historyvisits WHERE moz_places.id = moz_historyvisits.place_id ORDER BY moz_historyvisits.visit_date ASC;"
	for db in dbs:
		user = user_of(db)
		rows = query_sqlite(db, query)
		if not rows:
			continue
		for row in rows:
			if cfg["search"] and cfg["search"] not in row[1]:
				continue
			timestamp=datetime.datetime(1970,1,1)+datetime.timedelta(microseconds=row[0])
			# Append time, domain, title, url, browser, user
			csv_list.append([str(timestamp), urlparse(row[1]).hostname, row[2], row[1], "Firefox", user])
	write_lines(cfg["out_file"], csv_list)

# Find and parse SQLite databases for Chrome
def chrome_hist(cfg):
	csv_list = []
	dbs = find_dbs(os.path.join(os.path.join(cfg["mount_dir"],"Users",'*',"AppData","Local","Google","Chrome","User Data",'*',"History")))
	query = "SELECT urls.last_visit_time, urls.url, urls.title FROM urls, visits WHERE urls.id = visits.url ORDER BY visits.visit_time ASC"
	for db in dbs:
		user = user_of(db)
		rows = query_sqlite(db,query)
		if not rows:
			continue
		for row in rows:
			if cfg["search"] and cfg["search"] not in row[1]:
				continue
			timestamp = datetime.datetime(1601,1,1)+datetime.timedelta(microseconds=row[0])
			# Append time, domain, title, url, browser, user
			csv_list.append([str(timestamp), urlparse(row[1]).hostname, row[2], row[1], "Chrome", user])
	write_lines(cfg["out_file"], csv_list)

# Append entries to the CSV file
def write_lines(out_file, rows):
	filename = out_file
	out_rows = []
	with open(filename, 'ab') as output_file:
		writer = csv.writer(output_file)
		for row in rows:
			for i, value in enumerate(row):
				if value:
					value = value.encode('utf-8')
				row[i] = value
			out_rows.append(row)
		writer.writerows(out_rows)

# Read args, conditionally do things
def main():
	cfg = read_args()
	if cfg["firefox"] or cfg["all"]:
		firefox_hist(cfg)
	if cfg["chrome"] or cfg["all"]:
		chrome_hist(cfg)
	if cfg["ie"] or cfg["all"]:
		ie_hist(cfg)

main()
