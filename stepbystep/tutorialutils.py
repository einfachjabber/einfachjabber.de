#-*- coding: utf-8 -*-

import json
import os.path
from flask import abort
from stepbystep import app

class Tutorial():
    """Functions necessary for the tutorial-viewer to work"""

    def gettutorial(self, id):
        """Load the tutorial specified by id from the .json file"""
        from stepbystep.utils import errormail
        filename = app.config['TUTORIAL_PATH'] + id + '.json'
        print filename
        if os.path.isfile(filename):
            print "test"
            with open(filename, 'r') as f:
                try:
                    data = json.load(f)
                    return data
                except:
                    errormail('Error in JSON-Data')
                    abort(404)
        else:
            abort(404)

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

class OsCatalog():
    """docstring for Oscatalog"""

    def catlist(self):
        """docstring for catlist"""
        catlist = ['win', 'linux', 'osx', 'mobile']

    def oslist(self):
        """docstring for oslist"""
        listing = {
            'Linux': [
                    { 'name': 'Debian', 'short': 'debian' },
                    { 'name': 'Fedora', 'short': 'fedora' },
                    { 'name': 'Kubuntu', 'short': 'kubuntu' },
                    { 'name': 'OpenSUSE', 'short': 'opensuse' },
                    { 'name': 'Ubuntu', 'short': 'ubuntu' },
                    { 'name': 'Ubuntu Netbook Edition', 'short': 'ubuntunbe' },
                    ],
            'MacOSX': [],
            'Windows': [
                    { 'name': 'Windows Vista / 7', 'short': 'win7'},
                    { 'name': 'Windows XP', 'short': 'winxp' }
                   ],
            'Mobil': [
                    { 'name': 'Android', 'short': 'android' },
                    { 'name': 'Blackberry', 'short': 'blackberry'},
                    { 'name': 'iPhone', 'short': 'iphone' },
                    { 'name': 'Maemo2008', 'short': 'maemo2008'},
                   ],
            'Andere': [
                    { 'name': 'OpenSolaris', 'short': 'opensolaris'},
                    { 'name': 'PC BSD', 'short': 'pcbsd' }
                   ],
        }
        return listing

    def defclient(self, osystem):
        """Maps the OS short-names to their long pendants and their default client"""
        if osystem == 'android':
            system = ['Android', 'beem']
        if osystem == 'blackberry':
            system = ['Blackberry', 'None']
        if osystem == 'debian':
            system = ['Debian', 'pidgin']
        if osystem == 'fedora':
            system = ['Fedora', 'empathy']
        if osystem == 'iphone':
            system = ['iPhone', 'None']
        if osystem == 'kubuntu':
            system = ['Kubuntu', 'kopete']
        if osystem == 'macosx':
            system = ['Mac OS X', 'ichat']
        if osystem == 'maemo2008':
            system = ['Maemo OS2008', 'pidgin']
        if osystem == 'opensolaris':
            system = ['OpenSolaris', 'pidgin']
        if osystem == 'opensuse':
            system = ['OpenSUSE', 'kopete']
        if osystem == 'pcbsd':
            system = ['PC BSD', 'pidgin']
        if osystem == 'ubuntu':
            system = ['Ubuntu', 'empathy']
        if osystem == 'ubuntunbe':
            system = ['Ubuntu Netbook Edition', 'empathy']
        if osystem == 'win7':
            system = ['Windows Vista / 7', 'pidgin']
        if osystem == 'winxp':
            system = ['Windows XP', 'pidgin']
        return system
