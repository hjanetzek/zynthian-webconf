# -*- coding: utf-8 -*-
# ********************************************************************
# ZYNTHIAN PROJECT: Zynthian Web Configurator
#
# Mackie Controller Configuration
#
# Copyright (C) 2017-2024 Fernando Moyano <fernando@zynthian.org>
# Copyright (C) 2025 Christopher Matthews <chris@matthewsnet.de>
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

import os
import sys
import glob
import yaml
import shutil
import logging
import pexpect
import tornado.web
from subprocess import check_output, STDOUT
from collections import OrderedDict
import zynconf
from lib.zynthian_config_handler import ZynthianConfigHandler
import zyngine.zynthian_lv2 as zynthian_lv2

# sys.path.append(os.environ.get('ZYNTHIAN_UI_DIR'))

# ------------------------------------------------------------------------------
# Mackie Controller Configuration
# ------------------------------------------------------------------------------


class MackiecontrolHandler(ZynthianConfigHandler):

    # self.readonly_list = list(range(0, 40)) + list(range(104, 113))

    @tornado.web.authenticated
    def get(self, errors=None, config_template=None):
        template_path = f'{os.environ["ZYNTHIAN_UI_DIR"]}/zyngine/ctrldev/mackiecontrol'
        templates = [fn for fn in os.listdir(template_path) if fn.endswith('yaml')]
        logging.debug(f"Mackiecontrol templates: {templates}")

        mackie_config_path = f"{os.environ['ZYNTHIAN_CONFIG_DIR']}/ctrldev"
        mackie_config_file = f"{mackie_config_path}/mackiecontrol.yaml"

        if config_template:
            if config_template in templates:
                mackie_config_file = f"{template_path}/{config_template}"
        elif not os.path.isfile(mackie_config_file):
            # Not configured yet: the default template, as the driver does
            mackie_config_file = f"{template_path}/mackiecontrol.yaml"

        if errors is None:
            errors = []
        try:
            with open(mackie_config_file, 'r') as f:
                data = yaml.safe_load(f)
        except OSError as err:
            errors.append(f'file {mackie_config_file} not found: {err}')
        except yaml.YAMLError as err:
            errors.append(f'error reading {mackie_config_file} file: {err}')

        config = {
            '_SECTION_LOAD_TEMPLATE_': {
                'type': 'html',
                'content': "<h3>Load Template</h3>",
            },
            '_TEMPLATES_LOAD_': {
                'type': 'select',
                'title': 'Device Templates',
                'value': '',
                'options': [''] + sorted(templates),
                'refresh_on_change': True,
            },
            '_SECTION_DEVICE_SETTINGS_': {
                'type': 'html',
                'content': "<h3>Device Settings</h3>",
            },
            'name': {
                'type': 'text',
                'title': 'Mackie Profile Name',
                'value': data['device_settings']['name']
            },
            'number_of_strips': {
                'type': 'select',
                'title': 'Number of Strips',
                'value': str(data['device_settings']['number_of_strips']),
                'options': ['1', '2', '3', '4', '5', '6', '7', '8']
            },
            'masterfader': {
                'type': 'boolean',
                'title': 'Master Fader',
                'value': self.convert_boolean(data['device_settings']['masterfader'])
            },
            'masterfader_fader_num': {
                'type': 'select',
                'title': 'Master Fader Position Number (only relevant if the Master Fader is enabled)',
                'value': str(data['device_settings']['masterfader_fader_num']),
                'options': ['1', '2', '3', '4', '5', '6', '7', '8', '9']
            },
            'touchsensefaders': {
                'type': 'boolean',
                'title': 'Touch Sensitive Faders',
                'value': self.convert_boolean(data['device_settings']['touchsensefaders'])
            },
            'xtouch': {
                'type': 'boolean',
                'title': 'Behringer X-Touch',
                'value': self.convert_boolean(data['device_settings']['xtouch'])
            },
            '_SECTION_BUTTON_ASSIGNMENT_': {
                'type': 'html',
                'content': "<h3>Button Assignment</h3>",
                'advanced': True
            }
        }
        for ccnum in list(range(40, 104)):
            if ccnum in data["ccnum_buttons"].keys():
                config[str(ccnum)] = {
                    'type': 'text',
                    'title': f'{data["ccnum_buttons"][ccnum]["name"]} ({ccnum}) ',
                    'value': data['ccnum_buttons'][ccnum]['command'],
                    'advanced': True
                }

        if errors:
            logging.error("Mackiecontrol Action Failed: %s" % format(errors))

        super().get("Mackie Control Configuration", config, errors)

    @tornado.web.authenticated
    def post(self):
        errors = None
        template_path = f'{os.environ["ZYNTHIAN_UI_DIR"]}/zyngine/ctrldev/mackiecontrol'
        mackie_config_path = f"{os.environ['ZYNTHIAN_CONFIG_DIR']}/ctrldev"
        mackie_config_file = f"{mackie_config_path}/mackiecontrol.yaml"
        default_config_file = f"{template_path}/mackiecontrol.yaml"

        command = self.get_argument('_command')
        if command == 'SAVE':
            try:
                with open(default_config_file, 'r') as f:
                    data = yaml.safe_load(f)
                data['device_settings']['name'] = self.get_argument('name')
                data['device_settings']['number_of_strips'] = int(self.get_argument('number_of_strips'))
                data['device_settings']['masterfader_fader_num'] = int(self.get_argument('masterfader_fader_num'))
                for bool_setting in ['masterfader', 'xtouch', 'touchsensefaders']:
                    try:
                        self.get_argument(bool_setting)
                        data['device_settings'][bool_setting] = True
                    except:
                        data['device_settings'][bool_setting] = False
                strips = self.generate_strips(data['device_settings']['number_of_strips'])
                for ccnum in strips.keys():
                    data['ccnum_buttons'][ccnum] = strips[ccnum]

                for ccnum in list(range(40, 104)):
                    try:
                        command = self.get_argument(str(ccnum))
                        data['ccnum_buttons'][ccnum]['command'] = command
                    except:
                        pass

                with open(mackie_config_file, 'w') as f:
                    yaml.safe_dump(data, f, sort_keys=False)
                self.restart_ui_flag = True

            except OSError as err:
                errors = f'file {mackie_config_file} not saved: {err}'

            except Exception as err:
                logging.error(f"Error: {err}")
                errors = err
            self.get(errors)

        elif command == 'REFRESH':
            try:
                changed = self.get_argument('_changed')
                if changed == '_TEMPLATES_LOAD_':
                    got_template = self.get_argument('_TEMPLATES_LOAD_')
                    self.get(config_template=got_template)
            except Exception as err:
                self.get(err)

    def convert_boolean(self, mybool):
        if mybool:
            return "1"
        return "0"

    def rev_boolean(self, mystr):
        if mystr == '1':
            return True
        return False

    def generate_strips(self, number_or_strips):
        data = {}
        button = {
            'rec': 0,
            'solo': 8,
            'mute': 16,
            'select': 24,
            'encoderpress': 32,
            'fadertouch': 104
        }
        for key in button.keys():
            for i in range(0, 8):
                if i >= number_or_strips:
                    command = 'None'
                else:
                    command = f'mkc_{key}_{i}'
                data[i + button[key]] = {
                    'name': f'{key}_{i}',
                    'command': command
                }
        return data

# *****************************************************************************
