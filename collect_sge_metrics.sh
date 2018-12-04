#!/bin/bash

# I execute this script in crontab on services-7-1 every minute

source /etc/profile.d/sge.sh

python /data/users/jtatar/Work/Monitoring/sge-stats.influxdb.py &> /dev/null
