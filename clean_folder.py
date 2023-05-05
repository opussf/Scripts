#!/usr/bin/env python3
##
# clean_folder  --  clean up temporary folders
##
# Deletes everything under a folder which hasn't been modified
# in a week. Deletes directories that are empty, too.
###
# From:  http://www.oblomovka.com/wp/2008/08/29/

# From: http://stackoverflow.com/questions/2435580/tagging-files-with-colors-in-os-x-finder-from-shell-scripts
# osascript -e "tell application \"Finder\" to set label index of alias POSIX file \"$filename\" to $label"

import os, sys, time

if (len(sys.argv) == 2) and (sys.argv[1] == '-d'):
	dryrun = False
else:
	dryrun = True
	print("Starting dryrun:")

tmpdir = '/Users/opus/Downloads/Processed'
daysback = 8
cutofftime  = time.time() - (60 * 60 * 24 * daysback)

for d in os.walk(tmpdir, topdown=False):
	(dirpath, dirnames, filenames) = d
	for f in filenames:
		thisfile = os.path.join(dirpath, f)
		if (os.lstat(thisfile).st_mtime < cutofftime):
			try:
				if dryrun:
					print("I would delete:", thisfile)
				else:
					os.remove(thisfile)
			except OSError as err:
				print("%s: OSError(%s): %s" % (d, 5, err))

	for d in dirnames:
		thisdir = os.path.join(dirpath, d)
		if not os.listdir(thisdir):
			try:
				if dryrun:
					print("I would delete:", thisdir)
				else:
					os.rmdir(thisdir)
			except OSError as err:
				if (errno != 66):
					print("%s: OSError(%s): %s" % (d, 6, err))
if dryrun:
	print("Ending Dryrun")
