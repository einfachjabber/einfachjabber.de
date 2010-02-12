#!/usr/bin/python
#-*- coding: utf-8 -*-

from os import path
from datetime import datetime
from jinja2 import Environment, PackageLoader
from stepbystep.config import TEMPLATE_PATH, IMAGE_PATH
from werkzeug import Local, LocalManager, Response
from werkzeug.routing import Map, Rule
from stepbystep.tutorialutils import OsCatalog

local = Local()
local_manager = LocalManager([local])

### template-environment settings ###
jinja_env = Environment(loader=PackageLoader('stepbystep', TEMPLATE_PATH)) 
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
            #(outlink, url/endpoint, linktext),
            (False, 'start', 'Home'),
            (False, 'start', u'Jabber einfach erklärt'),
            (True, 'http://wiki.firefly-it.de/doku.php?id=jabber-projekt', 'Projekt-Wiki'),
            (False, 'start', 'Kontakt'),
    ]
    return links
jinja_env.globals['navigation'] = navigation()

def render_template(template, **context):
    return Response(jinja_env.get_template(template).render(**context),
                   mimetype='text/html')

def sendmail(name, email, mailbody):
    """function for sending all kinds of email"""
    from mailtools import SMTPMailer
    from stepbystep.config import MAILSERVER, MAILUSER, MAILPWD, MAILTO
    mailer = SMTPMailer(
        MAILSERVER,
        username=MAILUSER,
        password=MAILPWD,
        log_messages=False
    )

    mailer.send_plain(
        email,
        MAILTO,
        u'Kontaktformular stepbystep-it.de - Eine Nachricht',
        unicode(mailbody)
    )

