#!/bin/sh
SERVER="www.zz9-za.com"

DEPLOY=0

WARCRAFTFOLDER="/Applications/World of Warcraft/_retail_/"
PICTURE_SRC="$WARCRAFTFOLDER/Screenshots"
PICTURE_DEST="/Users/opus/Downloads/Processed/WowShots"
PICTURE_FILES=`ls "${PICTURE_SRC}"`
if [ ${#PICTURE_FILES} -gt 0 ]; then
	WORDS=`echo ${PICTURE_FILES} | wc -w`
	if [ ${DEPLOY} == 1 ]; then
		say "Deploying $WORDS screenshots" &
		rsync -tzhvicP --rsh='ssh -oPubkeyAcceptedAlgorithms=+ssh-rsa -oHostKeyAlgorithms=+ssh-dss -p2022' "${PICTURE_SRC}"/* opus@$SERVER:/home/opus/public_html/wowshots/imgs
		say "Deploy Complete."
	fi
	for file in ${PICTURE_FILES}; do
		mv "${PICTURE_SRC}/${file}" ~/Downloads/Processed/WowShots/
	done
    # Sort the files
    ~/Scripts/wowShots.py -d | say
else
	echo "No screen shots to send."
fi
