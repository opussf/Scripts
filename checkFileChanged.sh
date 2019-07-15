#!/bin/bash
# takes a file to check if changed
# retuns 0 if changed  (normal success)
# retuns 1 if not changed (normal failure)
# if check file does not exist, assume the file has changed

fileToCheck=$1
fileToCheckTmpName="/tmp/checkfile_"`md5 -q -s "$fileToCheck"`

# make sure checking file exists,
if [ -f "$fileToCheck" ]; then
	fileToCheckMD5=`md5 -q "$fileToCheck"`
else
	echo "$fileToCheck does not exist?"
fi

#echo $fileToCheckMD5
# get the contents, or use ""
if [ -f $fileToCheckTmpName ]; then
	tmpMD5=`cat $fileToCheckTmpName`
else
	tmpMD5=""
fi

if [ "$tmpMD5" != "$fileToCheckMD5" ]; then
	# file has not changed
	echo $fileToCheckMD5 > $fileToCheckTmpName
	say "file has changed.  Do something."
	exit 0
fi
exit 1
