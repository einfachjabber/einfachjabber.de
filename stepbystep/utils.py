#!/usr/bin/python
#-*- coding: utf-8 -*-

from os import path
from datetime import datetime
from creoleparser.dialects import create_dialect, creole10_base, creole11_base
from creoleparser.core import Parser
from jinja2 import Environment, PackageLoader
from stepbystep.config import TEMPLATE_PATH, IMAGE_PATH, ADMIN_MAIL
from werkzeug import Local, LocalManager, Response
from werkzeug.routing import Map, Rule
from stepbystep.tutorialutils import OsCatalog

local = Local()
local_manager = LocalManager([local])

### template-environment settings ###
jinja_env = Environment(loader=PackageLoader('stepbystep', TEMPLATE_PATH), extensions=['jinja2.ext.loopcontrols']) 
jinja_env.globals['imagepath'] = IMAGE_PATH
jinja_env.globals['currentyear'] = datetime.now().strftime("%Y")
jinja_env.globals['trackingcode'] = """ 
<!-- Piwik -->
<script type="text/javascript">
var pkBaseURL = (("https:" == document.location.protocol) ? "https://stats.firefly-it.de/" : "http://stats.firefly-it.de/");
document.write(unescape("%3Cscript src='" + pkBaseURL + "piwik.js' type='text/javascript'%3E%3C/script%3E"));
</script><script type="text/javascript">
try {
var piwikTracker = Piwik.getTracker(pkBaseURL + "piwik.php", 5);
piwikTracker.trackPageView();
piwikTracker.enableLinkTracking();
} catch( err ) {}
</script><noscript><p><img src="http://stats.firefly-it.de/piwik.php?idsite=5" style="border:0" alt=""/></p></noscript>
<!-- End Piwik Tag -->"""

jinja_env.globals['oslist'] = OsCatalog('None').oslist()

### URL Routing ###
url_map = Map()
url_map.add(Rule('/static/<file>', endpoint='static', build_only=True))
def expose(rule, **kw):
    '''Routing decorator'''
    def decorate(f):
        kw['endpoint'] = f.__name__
        url_map.add(Rule(rule, **kw))
        return f
    return decorate

def url_for(endpoint, _external=False, **values):
    """Build URLs from endpoint and values"""
    return local.url_adapter.build(endpoint, values, force_external=_external)
# making url_for available for templating
jinja_env.globals['url_for'] = url_for

def navigation():
    """Navigation links"""
    links = [
            #(outlink, url/endpoint, linktext, icon),
            (False, 'start', 'Home', 'home.png'),
            (False, 'jabber', 'Jabber?', 'jabber.png'),
            (False, 'oslist', 'Anleitungen', 'anleitungen.png'),
            (True, 'http://wiki.einfachjabber.de', 'Wiki', 'wiki.png'),
            (False, 'jabberreg', 'Neues Konto', 'neueskonto.png'),
            (False, 'help', 'Helfen', 'help.png'),
    ]
    return links
jinja_env.globals['navigation'] = navigation()

def render_template(template, **context):
    return Response(jinja_env.get_template(template).render(**context),
                   mimetype='text/html')

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
