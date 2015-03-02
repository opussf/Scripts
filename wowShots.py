#!/usr/bin/env python

import sys, os
from datetime import date

if (len(sys.argv) == 2) and (sys.argv[1] == '-d'):
	dryrun = False
else:
	dryrun = True
	print "Starting dryrun:"

baseDir = '/Users/opus/Downloads/Processed/WowShots'
folderNameFormat = "%y%m%d"
fileCount = 0

for root, dirs, files in os.walk(baseDir):
	if root == baseDir:  # only loop through the baseDir for files
		for f in files:
			fileName = os.path.join(root, f)
			mtime = int(os.lstat(fileName).st_mtime)
			fileDate = date.fromtimestamp(mtime).strftime(folderNameFormat)
			targetName = os.path.join(root, fileDate, f)

			if dryrun:
				print("I would move: %s -> %s" % (fileName, targetName))
			else:
				os.renames(fileName, targetName)
				fileCount += 1

print("Sorted %i files." % (fileCount,))
