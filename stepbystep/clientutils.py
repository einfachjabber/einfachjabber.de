#!/usr/bin/python
#-*- coding: utf-8 -*-

import os, glob, re
from werkzeug.exceptions import NotFound
from werkzeug.utils import cached_property
from stepbystep.config import TUTORIAL_PATH

class Clients(object):
    """Functions for managing the client-chooser"""
    
    def __init__(self, osystem):
        self.osystem = osystem

    @cached_property
    def clientlist(self):
        """reads the list of clients from the tutorial directory"""
        clist = []
        os.chdir(TUTORIAL_PATH)
        files = glob.glob(self.osystem + '*.json')
        if not files:
            raise NotFound()
        for i in files:
            i = re.sub(self.osystem + '-', '', i)
            i = re.sub('.json', '', i)
            clist = clist + [i]
        print(clist)
        return clist

    @cached_property
    def oslist(self):
        """Maps the OS short-names to their long pendants and their default client"""
        if self.osystem == 'winxp':
            system = ['Windows XP', 'pidgin']
        if self.osystem == 'win7':
            system = ['Windows 7', 'pidgin']
        if self.osystem == 'fedora':
            system = ['Fedora', 'empathy']
        if self.osystem == 'ubuntu':
            system = ['Ubuntu', 'empathy']
        if self.osystem == 'kubuntu':
            system = ['Kubuntu', 'kopete']
        return system


