#!/bin/bash

set -e

default_settings='/etc/sentry/sentry.conf.py'
custom_settings='/plugin/docker/sentry8.x/custom.conf.py'
if [ -f "$custom_settings" ]; then
    line="execfile('$custom_settings')"
	if ! grep -q "$line" "$default_settings"; then
		echo "$line" >> "$default_settings"
	fi
fi
if [ -d '/plugin' ]; then
    cd /plugin && python setup.py develop --user
fi

# first check if we're passing flags, if so
# prepend with sentry
if [ "${1:0:1}" = '-' ]; then
	set -- sentry "$@"
fi

case "$1" in
	celery|cleanup|config|createuser|devserver|django|export|help|import|init|plugins|repair|shell|start|upgrade)
		set -- sentry "$@"
	;;
	generate-secret-key)
		exec sentry config generate-secret-key
	;;
esac

exec "$@"
