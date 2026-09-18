#!/bin/bash
n=$(ps -eo args | grep -c "[p]rerender_audio")
echo "workers alive: $n"
ps -eo pid,rss,etime,args | grep "[p]rerender_audio" | sed 's/\(.\{100\}\).*/\1/'
free -h | sed -n 2p
