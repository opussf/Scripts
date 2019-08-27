#!/bin/bash
# takes a file to check if changed
# retuns 0 if changed  (normal success)
# retuns 1 if not changed (normal failure)
# if check file does not exist, assume the file has changed
# usage:  checkFileChanged.sh <file> && <do this on changed file>


fileToCheck=$1
fileToCheckTmpName="/tmp/checkfile_"`md5 -q -s "$fileToCheck"`

# make sure checking file exists,
if [ ! "$fileToCheck" ]; then
	echo "$fileToCheck does not exist?"
	exit 2  # this would keep it from runing anything if you are looking for success to continue
fi

if [ ! -f "$fileToCheckTmpName" ] || [ "$fileToCheck" -nt "$fileToCheckTmpName" ]; then
	# tmp file does not exist, OR file to check is newer
	touch "$fileToCheckTmpName"
	exit 0
fi
exit 1
