#!/bin/bash

webconf_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [ -f "$ZYNTHIAN_SYS_DIR/scripts/zynthian_envars_extended.sh" ]; then
	# ZynthianOS: the environment of zynthian-sys
	source "$ZYNTHIAN_SYS_DIR/scripts/zynthian_envars_extended.sh"
	# 10=DEBUG, 20=INFO, 30=WARNING, 40=ERROR, 50=CRITICAL
	export ZYNTHIAN_LOG_LEVEL=10
	export ZYNTHIAN_WEBCONF_LOG_LEVEL=10
else
	# Elsewhere (a desktop checkout, distribution packages like Nura's): zynthian-ui's desktop
	# environment (the directories, ZYNTHIAN_DESKTOP=1) and the user's zynthian configuration,
	# as zynthian-ui's desktop/zynthian_desktop.sh loads them
	ui_dir="${ZYNTHIAN_UI_DIR:-/usr/share/zynthian/zynthian-ui}"
	if [ ! -f "$ui_dir/desktop/zynthian_desktop_env.sh" ]; then
		echo "zynthian-ui not found in $ui_dir (set ZYNTHIAN_UI_DIR)" >&2
		exit 1
	fi
	export ZYNTHIAN_UI_DIR="$ui_dir"
	source "$ui_dir/desktop/zynthian_desktop_env.sh"
	for f in "$ZYNTHIAN_CONFIG_DIR/zynthian_envars.sh" "$ZYNTHIAN_CONFIG_DIR/zynthian_custom_config.sh"; do
		[ -f "$f" ] && source "$f"
	done
	if [ -f "$ZYNTHIAN_VENV_DIR/bin/activate" ]; then
		source "$ZYNTHIAN_VENV_DIR/bin/activate"
	fi
	# Python packages bundled with the packages (zynthian-ui's, then this one's)
	for d in /usr/share/zynthian/python "$webconf_dir/python"; do
		[ -d "$d" ] && export PYTHONPATH="$d${PYTHONPATH:+:$PYTHONPATH}"
	done
	# Not root: not port 80 by default
	export ZYNTHIAN_WEBCONF_PORT="${ZYNTHIAN_WEBCONF_PORT:-8080}"
	export ZYNTHIAN_LOG_LEVEL="${ZYNTHIAN_LOG_LEVEL:-20}"
	export ZYNTHIAN_WEBCONF_LOG_LEVEL="${ZYNTHIAN_WEBCONF_LOG_LEVEL:-20}"
fi
export ZYNTHIAN_WEBCONF_DIR="${ZYNTHIAN_WEBCONF_DIR:-$webconf_dir}"

cd "$webconf_dir"
exec python3 ./zynthian_webconf.py
