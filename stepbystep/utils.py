#-*- coding: utf-8 -*-

from os import path, chdir
import json
from glob import glob
from datetime import datetime
from creoleparser.dialects import create_dialect, creole10_base, creole11_base
from creoleparser.core import Parser
from flaskext.mail import Message
from stepbystep import app
from flask import abort

class Tutorial():
    """Functions necessary for the tutorial-viewer to work"""

    def gettutorial(self, id):
        """Load the tutorial specified by id from the .json file"""
        filename = app.config['TUTORIAL_PATH'] + id + '.json'
        if path.isfile(filename):
            with open(filename, 'r') as f:
                try:
                    data = json.load(f)
                    return data
                except:
                    app.logger.error('Error in JSON-Data')
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

    def oslist(self):
        """builds the menu for /os"""
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

class Clients():
    """Functions for managing the client-chooser"""

    def clientlist(self, osystem):
        """reads the list of clients from the tutorial directory"""
        clist = []
        chdir(app.config['TUTORIAL_PATH'])
        files = glob(osystem + '-*.json')
        if not files:
            abort(404)
        for file in files:
            with open(file, 'r') as f:
                try:
                    clname = json.load(f)['client']
                    clist = clist + [clname]
                except:
                    app.logger.error('Error in JSON-Data')
                    abort(404)
        return clist

def sendmail(mailtype, data=None):
    '''
    Mail dispatcher

    :param mailtype: can be 'error' or 'mailreminder'
    :param data: data for mail-forming, depends on mailtype
    '''
    if data:
        msg = Message('[einfachJabber.de] Jabber-Konto Registrierung')
        msg.body = '''
einfachJabber.de

Du hast eben über http://einfachjabber.de einen neuen
Jabber-Account registriert.
Die Benutzerdaten dazu lauten:

Benutzername: %s
Passwort: %s

Auf http://einfachjabber.de findest du Anleitungen für
verschiedene Client-Programme.
        ''' % (data[1], data[2])
    msg.recipients = [data[0]]
    msg.send()

my_parser = Parser(dialect=create_dialect(creole11_base), method='html', encoding=None)
