# -*- coding: utf-8 -*-
"""
    einfachjabber.forms
    ~~~~~~~~~~~~~~~~

    Definition of the jabber registration form

    :copyright: (c) 2010 by Benjamin Zimmer.
    :license: MIT, see LICENSE for more details.
"""

import random
from wtforms import Form, TextField, TextAreaField, SelectField,\
                    PasswordField, HiddenField, validators
from einfachjabber.utils import sendmail

serverlist = [
        ('alpha-labs.net', 'alpha-labs.net'),
        ('einfachjabber.de', 'einfachjabber.de'),
        ('freies-im.de', 'freies-im.de'),
        ('jabber.rootbash.com', 'jabber.rootbash.com'),
        ('jabber-server.de', 'jabber-server.de'),
        ('jabberim.de', 'jabberim.de'),
        ('jabme.de', 'jabme.de'),
        ('open-host.de', 'open-host.de')
    ]

def randomserver():
    server = []
    sl = serverlist[:]
    while sl:
        element = random.choice(sl)
        sl.remove(element)
        server.append(element)

    return server


class RegForm(Form):
    nick    = TextField(u'gewünschte Jabber-Adresse',
                        [validators.Required(message=u'Bitte einen\
                                                     Namen angeben.')
                                ])
    domain  = SelectField(u'Domain')
    email   = TextField(u'E-Mail (optional)',
                                [validators.Optional(),\
                                validators.Email(message=u'Du hast leider\
                                                    keine valide E-Mail\
                                                    Adresse angegeben. Bitte\
                                                    versuche es erneut.')
                                  ])
    passwd  = PasswordField(u'Passwort', [validators.Required(
                                                    message=u'Bitte gib ein\
                                                    Passwort ein.')
                                                ])
    recaptcha_challenge_field = TextAreaField()
    recaptcha_response_field = HiddenField()

class RateForm(Form):
    rating  = SelectField(u'Bewertung:')
    hint    = TextAreaField(u'Verbesserungsvorschlag (optional)')

