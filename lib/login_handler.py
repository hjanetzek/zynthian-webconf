# -*- coding: utf-8 -*-
# ********************************************************************
# ZYNTHIAN PROJECT: Zynthian Web Configurator
#
# Login Handler
#
# Copyright (C) 2017 Fernando Moyano <jofemodo@zynthian.org>
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
import getpass
import logging
import tornado.web

# PAM bindings: PyPAM ("import PAM", Debian's python3-pam, ZynthianOS) or python-pam ("import pam",
# PyPI and Alpine's py3-pam)
try:
    import PAM
    pam = None
except ImportError:
    PAM = None
    import pam

# The account whose password logs in: root on ZynthianOS (webconf runs as root), else the user
# webconf runs as (the device user on Nura); ZYNTHIAN_WEBCONF_USER to choose another
LOGIN_USER = os.environ.get("ZYNTHIAN_WEBCONF_USER") or ("root" if os.geteuid() == 0 else getpass.getuser())

# Development: ZYNTHIAN_WEBCONF_NO_AUTH=1 logs in without a password (the server then listens on
# 127.0.0.1 only, see zynthian_webconf.py)
NO_AUTH = os.environ.get("ZYNTHIAN_WEBCONF_NO_AUTH") == "1"

# ------------------------------------------------------------------------------
# Login Handler
# ------------------------------------------------------------------------------


class LoginHandler(tornado.web.RequestHandler):

    def get(self, errors=None):
        if NO_AUTH:
            self.login()
            return
        self.render("config.html", info={}, body="login_block.html",
                    title="Login", config=None, errors=errors)

    def login(self):
        self.set_secure_cookie("user", LOGIN_USER, expires_days=3650)
        if self.get_argument("next", ""):
            self.redirect(self.get_argument("next"))
        else:
            self.redirect("/")

    def post(self):
        password = self.get_argument("PASSWORD")
        try:
            ok, error = self.authenticate(LOGIN_USER, password)
        except Exception as e:
            logging.error(e)
            self.get({"PASSWORD": "Authentication Failure"})
            return
        if not ok:
            logging.info(f"Incorrect password => {error}")
            self.get({"PASSWORD": "Incorrect Password"})
            return
        self.login()

    @staticmethod
    def authenticate(user, password):
        """Check the password of user with PAM; returns (ok, error message)"""
        if PAM is None:
            p = pam.pam()
            if p.authenticate(user, password, service="passwd"):
                return True, None
            return False, f"{p.code} {p.reason}"

        def pam_conv(auth, query_list, userData):
            resp = []
            for i in range(len(query_list)):
                query, type = query_list[i]
                if type in (PAM.PAM_PROMPT_ECHO_ON, PAM.PAM_PROMPT_ECHO_OFF):
                    resp.append((password, 0))
                elif type == PAM.PAM_PROMPT_ERROR_MSG or type == PAM.PAM_PROMPT_TEXT_INFO:
                    logging.error(query)
                    resp.append(('', 0))
                else:
                    return None
            return resp

        auth = PAM.pam()
        auth.start("passwd")
        auth.set_item(PAM.PAM_USER, user)
        auth.set_item(PAM.PAM_CONV, pam_conv)
        try:
            auth.authenticate()
            auth.acct_mgmt()
        except PAM.error as resp:
            return False, resp
        return True, None

    @staticmethod
    def change_password(user, old_password, new_password):
        """Set a new password for user (after authenticate); raises an exception on failure.
        PyPAM: chauthtok as root (ZynthianOS). Otherwise passwd(1): as root for any user, as that
        user for itself (it asks for the old password then)."""
        if PAM is not None:
            def pam_conv(auth, query_list, userData):
                resp = []
                for query, type in query_list:
                    if type in (PAM.PAM_PROMPT_ECHO_ON, PAM.PAM_PROMPT_ECHO_OFF):
                        resp.append((new_password, 0))
                    else:
                        resp.append(('', 0))
                return resp
            auth = PAM.pam()
            auth.start("passwd")
            auth.set_item(PAM.PAM_USER, user)
            auth.set_item(PAM.PAM_CONV, pam_conv)
            auth.chauthtok()
            return
        import pexpect
        cmd = ["passwd", user] if os.geteuid() == 0 else ["passwd"]
        child = pexpect.spawn(cmd[0], cmd[1:], timeout=10, encoding="utf-8")
        answers = 0
        while True:
            i = child.expect([r"(?i)(current|old).*password", r"(?i)password", pexpect.EOF])
            if i == 0:
                child.sendline(old_password)
            elif i == 1:
                child.sendline(new_password)
                answers += 1
            else:
                break
        child.close()
        if child.exitstatus != 0 or answers < 2:
            raise RuntimeError(f"passwd failed ({child.exitstatus}): {child.before.strip()}")


class LogoutHandler(tornado.web.RequestHandler):
    def get(self):
        self.clear_cookie('user')
        self.redirect(self.get_argument('next', '/'))
