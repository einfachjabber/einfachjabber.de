#-*- coding: utf-8 -*-

from os import path, chdir
import json
from glob import glob
from datetime import datetime
from creoleparser.dialects import create_dialect, creole10_base, creole11_base
from creoleparser.core import Parser
from flaskext.mail import Message
from einfachjabber.extensions import mail
from flask import abort, current_app

class Tutorial():
    """Functions necessary for the tutorial-viewer to work"""

    def gettutorial(self, id):
        """Load the tutorial specified by id from the .json file"""
        filename = current_app.config['TUTORIAL_PATH'] + id + '.json'
        if path.isfile(filename):
            with open(filename, 'r') as f:
                try:
                    data = json.load(f)
                    return data
                except:
                    current_app.logger.error('Error in JSON-Data')
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

def sendmail(mailtype, data=None):
    '''
    Mail dispatcher

    :param mailtype: can be 'error', 'rating' or 'mailreminder'
    :param data: data for mail-forming, depends on mailtype
    '''
    if data:
        if mailtype is 'mailreminder':
            msg = Message('[einfachJabber.de] Jabber-Konto Registrierung')
            msg.body = u'''
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

        if mailtype is 'rating':
            msg = Message('[einfachJabber.de] Tutorialbewertung')
            msg.body = u'''
    einfachJabber.de Tutorialbewertung

    Bewertung: %s
    Vorschlag: %s
    Tutorial: %s
            ''' % (data[0], data[1], data[2])
            msg.recipients = ['bz@einfachjabber.de']
        mail.send(msg)

my_parser = Parser(dialect=create_dialect(creole11_base), method='html', encoding=None)
