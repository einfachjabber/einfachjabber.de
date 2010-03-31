#!/usr/bin/python
#-*- coding: utf-8 -*-

from os import path

TEMPLATE_PATH = 'templates'
STATIC_PATH = path.join(path.dirname(__file__), 'static')
IMAGE_PATH = 'static/images/'
TUTORIAL_PATH = STATIC_PATH +'/tutorials/'

MAILSERVER = '78.47.69.2'
MAILUSER = 'zero@zeroathome.de'
MAILPWD = ''
MAILTO = [u'']
MAILFROM = u'zero@zeroathome.de'
ADMIN_MAIL = u'bz@einfachjabber.de'

PAYPAL_BUTTON = u'\
<form action="https://www.paypal.com/cgi-bin/webscr" method="post">\
<fieldset>\
<input type="hidden" name="cmd" value="_s-xclick" />\
<input type="hidden" name="hosted_button_id" value="6PLNS8GTG4HCL" />\
<input type="image" src="/static/images/ui/\
paypal-mb.png" name="submit"\
 alt="Jetzt einfach, schnell und sicher online bezahlen – mit PayPal." />\
<img alt="" src="https://www.paypal.com/de_DE/i/scr/pixel.gif"\
 width="1" height="1" />\
</fieldset>\
</form>\
'
