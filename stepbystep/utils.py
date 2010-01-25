from os import path
from datetime import datetime
from jinja2 import Environment, PackageLoader
from werkzeug import Local, LocalManager, Response
from werkzeug.routing import Map, Rule
from stepbystep.config import TEMPLATE_PATH, IMAGE_PATH

local = Local()
local_manager = LocalManager([local])


jinja_env = Environment(loader=PackageLoader('stepbystep', TEMPLATE_PATH)) 
jinja_env.globals['imagepath'] = IMAGE_PATH
jinja_env.globals['currentyear'] = datetime.now().strftime("%Y")

url_map = Map()
url_map.add(Rule('/static/<file>', endpoint='static', build_only=True))
def expose(rule, **kw):
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
            ('willkommen', 'Home'),
            ('services', 'Services'),
            ('portfolio', 'Portfolio'),
            ('kontakt', 'Kontakt'),
            ('impressum', 'Impressum'),
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

