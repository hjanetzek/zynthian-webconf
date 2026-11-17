# -*- coding: utf-8 -*-
# ********************************************************************
# ZYNTHIAN PROJECT: Zynthian Web Configurator
#
# The CUIA names for the wiring, MIDI options and key binding pages
#
# ********************************************************************
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License as
# published by the Free Software Foundation; either version 2 of
# the License, or any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# For a full copy of the GNU General Public License see the LICENSE.txt file.
#
# ********************************************************************

import logging

# zyngui.zynthian_cuia_list has the names without the Tk UI. An older zynthian-ui only has
# them on zynthian_gui, which imports the whole Tk UI (tkinter, PIL, websocket_server, ...):
# if that fails too, the pages offer no CUIAs, but webconf keeps running.
try:
    from zyngui.zynthian_cuia_list import get_cuia_list as _get_cuia_list
except Exception as e:
    logging.info(f"No zyngui.zynthian_cuia_list ({e}), the CUIA list from zynthian_gui")
    try:
        from zyngui.zynthian_gui import zynthian_gui
        _get_cuia_list = zynthian_gui.get_cuia_list
    except Exception as e:
        logging.warning(f"Can't import the CUIA list ({e}): the pages offer no CUIAs")
        _get_cuia_list = None


def get_cuia_list():
    """The CUIA names, an empty list if zynthian-ui has none to offer."""
    if _get_cuia_list is None:
        return []
    try:
        return list(_get_cuia_list())
    except Exception as e:
        logging.warning(f"Can't get the CUIA list: {e}")
        return []
