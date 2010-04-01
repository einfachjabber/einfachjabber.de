#!/usr/bin/env python
#-*- coding: utf-8 -*-

import xmpp
import xmpp.debug as dbug

dbug.Debug = dbug.NoDebug

class RegError(Exception):
    """Handle account registration errors"""
    def __init__(self, lastErr):
        Exception.__init__(self)
        self.lastErr = lastErr
        if lastErr == 'conflict':
            self.errtext = 'Dieser Benutzername ist bereits vergeben.'
        else:
            self.errtext = 'Ein Fehler ist aufgetreten. Bitte versuche es erneut.'


        
def xmppreg(username, passwd, domain):
    """docstring for xmppreg"""

    c = xmpp.Client(domain)
    c.connect()
    reg = xmpp.features.register(c, domain, {'username': username, 'password': passwd})
    print(reg)
    if reg is None:
        return 0, c.lastErr
    else:
        return 1, 'None'

    c.disconnect

