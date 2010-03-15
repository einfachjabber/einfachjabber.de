#!/usr/bin/python
#-*- coding: utf-8 -*-

import json
import os.path
from werkzeug.exceptions import NotFound
from werkzeug.utils import cached_property
from stepbystep.config import TUTORIAL_PATH

class Tutorial(object):
    """Functions necessary for the tutorial-viewer to work"""

    def __init__(self, id):
        self.id = id

    @cached_property
    def gettutorial(self):
        """Load the tutorial specified by id from the .json file"""
        filename = TUTORIAL_PATH + self.id + '.json'
        if os.path.isfile(filename):
            with open(filename, 'r') as f:
                data = json.load(f)
            return data
        else:
            raise NotFound()

    def pagination(self, page, maxpage):
        """pagination helper"""
        flpage = 1
        if page == 0:
            flpage = 0
        elif page == maxpage:
            flpage = 2
        elif page > maxpage:
            raise NotFound()
        return flpage

class OsCatalog(object):
    """docstring for Oscatalog"""
    def __init__(self, osystem):
        self.osystem = osystem

    def catlist(self):
        """docstring for catlist"""
        catlist = ['win', 'linux', 'osx', 'mobile']

    def oslist(self):
        """docstring for oslist"""
        listing = {
            'Windows': [
                    { 'name': 'Windows Vista / 7', 'short': 'win7'},
                    { 'name': 'Windows XP', 'short': 'winxp' }
                   ],
            'Linux': [
                    { 'name': 'Debian', 'short': 'debian' },
                    { 'name': 'Fedora', 'short': 'fedora' },
                    { 'name': 'Kubuntu', 'short': 'kubuntu' },
                    { 'name': 'OpenSUSE', 'short': 'opensuse' },
                    { 'name': 'Ubuntu', 'short': 'ubuntu' },
                    ],
            'MacOSX': [],
            'Mobil': [
                    { 'name': 'Android', 'short': 'android' },
                    #{ 'name': 'Blackberry', 'short': 'blackberry'},
                    { 'name': 'iPhone', 'short': 'iphone' },
                    { 'name': 'Maemo2008', 'short': 'maemo2008'},
                    #{ 'name': 'Palm (Pre) WebOS', 'short': 'webos'},
                    #{ 'name': 'Symbian S60', 'short': 's60'}
                   ],
        }
        return listing

    @cached_property
    def defclient(self):
        """Maps the OS short-names to their long pendants and their default client"""
        if self.osystem == 'android':
            system = ['Android', 'beem']
        if self.osystem == 'debian':
            system = ['Debian', 'pidgin']
        if self.osystem == 'fedora':
            system = ['Fedora', 'empathy']
        if self.osystem == 'iphone':
            system = ['iPhone', 'None']
        if self.osystem == 'kubuntu':
            system = ['Kubuntu', 'kopete']
        if self.osystem == 'maemo2008':
            system = ['Maemo OS2008', 'pidgin']
        if self.osystem == 'opensuse':
            system = ['OpenSUSE', 'kopete']
        if self.osystem == 'ubuntu':
            system = ['Ubuntu', 'empathy']
        if self.osystem == 'win7':
            system = ['Windows Vista / 7', 'pidgin']
        if self.osystem == 'winxp':
            system = ['Windows XP', 'pidgin']
        return system


