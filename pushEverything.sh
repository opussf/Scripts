#!/bin/sh
SERVER="www.zz9-za.com"

PICTURE_SRC="/Users/opus/Downloads/Everything/"
PICTURE_DEST="/Users/opus/Downloads/Processed/WowShots"
PICTURE_FILES=`ls "${PICTURE_SRC}"`
if [ ${#PICTURE_FILES} -gt 0 ]; then
	rsync -zhvicPrt --delete --rsh='ssh -p2022' "${PICTURE_SRC}" opus@$SERVER:/home/opus/public_html/Everything/imgs --exclude '.cache*' --exclude '.DS_*' --exclude 'START*' --exclude 'DONE*'
fi
