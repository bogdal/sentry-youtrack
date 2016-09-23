#!/bin/bash

set -e

default_settings='/etc/sentry/sentry.conf.py'
custom_settings='/plugin/docker/sentry/custom.conf.py'
if [ -f "$custom_settings" ]; then
    line="execfile('$custom_settings')"
	if ! grep -q "$line" "$default_settings"; then
		echo "$line" >> "$default_settings"
	fi
fi
if [ -d '/plugin' ]; then
    cd /plugin && python setup.py develop
fi

/entrypoint.sh $@
