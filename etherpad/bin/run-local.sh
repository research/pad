#!/bin/bash -e

#  Copyright 2009 Google Inc.
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS-IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.

mkdir -p data/appjet

# set some reasonable defaults... OVERRIDDEN BELOW
MXRAM="512M"
#MAXTHREADS="128" # not using

if [ -x "/usr/bin/perl" ]; then
	if [ -e "/proc/meminfo" ]; then
	MXRAM=$(cat /proc/meminfo | perl -ne '
		BEGIN {
			$free = 0;
			$buffers = 0;
			$cached = 0
		};

		if (m/^MemFree:\s*(\d+)/)
			{ $free = $1/1024 };
		if (m/^Buffers:\s*(\d+)/)
			{ $buffers = $1/1024 };
		if (m/^Cached:\s*(\d+)/)
			{ $cached = $1/1024 };

		END {
			$usable_free = ($free + $buffers + $cached)/1.25;
			$usable_free = 100 if ($usable_free < 100);
			$usable_free = 20480 if ($usable_free > 20480);
			print int($usable_free)."M\n"
		};
    ')
    MAXPERM=$(echo "$MXRAM" | perl -ne '
        s/[^\d]//;
        $maxperm = int($_/64);
        if ($maxperm < 32)
            { $maxperm = 32 }
        print $maxperm."M\n";
    ')
	fi
fi


if [ ! -z $1 ]; then
    if [ ! '-' = `echo $1 | head -c 1` ]; then
        MXRAM="$1";
        shift;
    fi
fi

CP=""
if [[ $(uname -s) == CYGWIN* ]]; then
    _tmp=`readlink -f "appjet-eth-dev.jar"`
    CP=`cygpath -wp "${_tmp}"`
    _tmp=`readlink -f "data"`
    CP="${CP}\;"`cygpath -wp "${tmp}"`
    for f in `readlink -f "lib/*.jar"`; do
            CP="$CP\;"`cygpath -wp "${f}"`
    done
else
    CP="appjet-eth-dev.jar:data"
    for f in lib/*.jar; do
        CP="$CP:$f"
    done
fi


if [ -z "$JAVA" ]; then
    JAVA=java
fi

if [[ $(uname -s) == CYGWIN* ]]; then
    JAVA=java
fi

# etherpad properties file
cfg_file=./etc/etherpad.local.properties
if [ ! -f $cfg_file ]; then
  cfg_file=./etc/etherpad.localdev-default.properties
fi
if [[ $1 == "--cfg" ]]; then
  cfg_file=${2}
  shift;
  shift;
fi

echo "Maximum ram: $MXRAM"
#echo "Maximum thread count: $MAXTHREADS"

echo "Using config file: ${cfg_file}"

exec $JAVA -classpath $CP \
    -server \
    -Xmx${MXRAM} \
    -Xms${MXRAM} \
    -Djava.awt.headless=true \
    -XX:MaxGCPauseMillis=500 \
    -XX:+UseG1GC \
    -XX:+PrintGCDetails \
    -XX:+PrintGCTimeStamps \
    -XX:+PrintGCDateStamps \
    -Xloggc:/var/log/etherpad/`hostname`-gc-`date +%Y%m%d%H%M`.log \
    -Dappjet.jmxremote=true \
    $JAVA_OPTS \
    net.appjet.oui.main \
    --configFile=${cfg_file} \
    "$@"

