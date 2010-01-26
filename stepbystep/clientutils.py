#!/usr/bin/python
#-*- coding: utf-8 -*-

import os, glob, re
from werkzeug.exceptions import NotFound
from stepbystep.config import TUTORIAL_PATH

class Clients(object):
    """Functions for managing the client-chooser"""
    
    def clientlist(self, osystem):
        """reads the list of clients from the tutorial directory"""
        clist = []
        os.chdir(TUTORIAL_PATH)
        files = glob.glob(osystem + '*.json')
        if not files:
            raise NotFound()
        for i in files:
            i = re.sub(osystem + '-', '', i)
            i = re.sub('.json', '', i)
            clist = clist + [i]
            
        return clist

    def oslist(self, osystem):
        """Maps the OS short-names to their long pendants"""
        if osystem == 'winxp':
            system = ['Windows XP', 'pidgin']
        if osystem == 'winvista':
            system = ['Windows Vista', 'pidgin']
        if osystem == 'win7':
            system = ['Windows 7', 'pidgin']
        return system


