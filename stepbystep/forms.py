#!/usr/bin/python
#-*- coding: utf-8 -*-

from wtforms import Form, TextField, TextAreaField, validators
from stepbystep.utils import sendmail

class ContactForm(Form):
    name    = TextField('Name', [validators.Required(message=u'Bitte einen\
                                                     Namen angeben, damit\
                                                     wir Sie persönlich\
                                                     erreichen können.')
                                ])
    email   = TextField('E-Mail', [validators.Length(min=5, 
                                                     max=120, 
                                                     message=u'Ihre E-Mail\
                                                     Adresse ist zu kurz,\
                                                     bitte überprüfen Sie\
                                                     noch einmal die\
                                                     Eingabe'),
                                   validators.Email(message=u'Sie haben leider\
                                                    keine valide E-Mail\
                                                    Adresse angegeben. Bitte\
                                                    versuchen Sie es erneut.')
                                  ])
    message = TextAreaField('Nachricht/Frage', [validators.Required(
                                                    message=u'Sie haben leider\
                                                    vergessen uns Ihr Anliegen\
                                                    mitzuteilen. Bitte füllen\
                                                    Sie das Feld Nachricht aus')
                                                ])

def composemail(name, email, message):
    """Use the form-contents to create an email to send"""
    mailbody = 'Eine Nachricht von ' + str(name) + ' (' + str(email)\
                + ')\n\n' + 'Nachricht:\n' + message
    sendmail(name, email, message)

