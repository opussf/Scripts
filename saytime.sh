#!/bin/sh
#ps aux | grep Warcraft | grep -v grep >> /dev/null && say "Wow is running."
#ps aux | grep Warcraft | grep -v grep >> /dev/null || say "Wow is NOT running."

ps aux | grep Warcraft | grep -v grep >> /dev/null || say `date "+%H hours %M."`
