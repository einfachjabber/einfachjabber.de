#-*- coding: utf-8 -*-

from os import path
from datetime import datetime
from creoleparser.dialects import create_dialect, creole10_base, creole11_base
from creoleparser.core import Parser
import logging

logger = logging.getLogger('einfachjabber.de')
hdlr = logging.FileHandler('/var/log/einfachjabber.log')
formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
hdlr.setFormatter(formatter)
logger.addHandler(hdlr)
logger.setLevel(logging.INFO)



def sendmail(email, subject, mailbody):
    """function for sending all kinds of email"""
    from mailtools import SMTPMailer
    from stepbystep.config import MAILSERVER, MAILUSER, MAILPWD, MAILFROM
    mailer = SMTPMailer(
        MAILSERVER,
        username=MAILUSER,
        password=MAILPWD,
        log_messages=False
    )
    mailer.send_plain(
        MAILFROM,
        email,
        subject,
        mailbody
    )

def errormail(error):
    """Send mail to admins on critical site errors"""
    mailbody = u'Error on site in ' + error
    subject = u'einfachJabber.de - Fehler auf der Seite'
    email = ADMIN_MAIL
    sendmail(email, subject, mailbody)

my_parser = Parser(dialect=create_dialect(creole11_base), method='html', encoding=None)
