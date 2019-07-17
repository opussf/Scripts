#!/bin/bash
SERVER="www.zz9-za.com"

WARCRAFTFOLDER="/Applications/World of Warcraft"
LOG_SRC="$WARCRAFTFOLDER/Logs"

LOG_FILE="$LOG_SRC/WoWCombatLog.txt"
#say "sending combat log" &
rsync -tzhvicP --rsh='ssh -p2022' "$LOG_FILE" opus@$SERVER:/home/opus/public_html/wowcombat/
#say "combat log complete"
