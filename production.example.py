#-*- coding: utf-8 -*-

DEBUG = False
TESTING = False

from os import path

STATIC_PATH = path.join(path.dirname(__file__), 'einfachjabber/static')
TUTORIAL_PATH = path.join(STATIC_PATH, 'tutorials/')

MAIL_SERVER = ''
MAIL_USERNAME = ''
MAIL_PASSWORD = ''
MAILTO = [u'']
DEFAULT_MAIL_SENDER = u''
ADMINS = ['']

# Donation Stuff
PAYPAL_BUTTON = u'''
'''
FLATTR_BUTTON = u'''
'''
