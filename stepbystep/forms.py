#!/usr/bin/python
#-*- coding: utf-8 -*-

import random
from wtforms import Form, TextField, TextAreaField, SelectField,\
                    PasswordField, HiddenField, validators
from stepbystep.utils import sendmail

serverlist = [
    ('alpha-labs.net', 'alpha-labs.net'),
    #('brauchen.info', 'brauchen.info'),
    #('deshalbfrei.org', 'deshalbfrei.org'),
    #('draugr.de', 'draugr.de'),
    ('freies-im.de', 'freies-im.de'),
    #('jabber.ccc.de', 'jabber.ccc.de'),
    ('jabber.rootbash.com', 'jabber.rootbash.com'),
    ('jabber-server.de', 'jabber-server.de'),
    ('jabberim.de', 'jabberim.de'),
    #('jabme.de', 'jabme.de'),
    ('open-host.de', 'open-host.de'),
    #('na-di.de', 'na-di.de'),
    #('neko.im', 'neko.im'),
    #('ubuntu-jabber.de', 'ubuntu-jabber.de'),
    #('ubuntu-jabber.net', 'ubuntu-jabber.net'),
    #('verdammung.org', 'verdammung.org'),
    #('xabber.de', 'xabber.de'),
    #('firefly-it.de', 'firefly-it.de'),
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



