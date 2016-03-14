#!/bin/bash

set -e

if [ "$1" = 'sentry' ]; then
	defaultConf='/home/user/.sentry/sentry.conf.py'
	linksConf='/home/user/docker-links.conf.py'
    pluginConf='/plugin/docker/sentry/custom.conf.py'

	if [ ! -s "$defaultConf" ]; then
		sentry init "$defaultConf"
	fi

	line="execfile('$linksConf')"
	if ! grep -q "$line" "$defaultConf"; then
		echo "$line" >> "$defaultConf"
	fi
    if [ -f "$pluginConf" ]; then
        line="execfile('$pluginConf')"
    	if ! grep -q "$line" "$defaultConf"; then
    		echo "$line" >> "$defaultConf"
    	fi
    fi
    if [ -d '/plugin' ]; then
        cd /plugin && python setup.py develop --user
    fi
fi

exec "$@"
