# -*- coding: utf-8 -*-
"""
    einfachjabber
    ~~~~~~~~~~

    :copyright: (c) 2010 by Benjamin Zimmer.
    :license: MIT, see LICENSE for more details.
"""

import re
from flask import Flask, request, session, g, redirect, url_for, \
        abort, render_template, flash
from flaskext.mail import Mail, Message

app = Flask(__name__)
app.config.from_envvar('SBS_SETTINGS')
mail = Mail(app)

if not app.debug:
    import logging
    from logging import FileHandler
    from logging.handlers import SMTPHandler

    mail_handler = SMTPHandler(app.config['MAIL_SERVER'],
                               app.config['DEFAULT_MAIL_SENDER'],
                               app.config['ADMINS'],
                               '[einfachJabber.de] Failed',
                               (app.config['MAIL_USERNAME'],
                                app.config['MAIL_PASSWORD']))
    mail_handler.setLevel(logging.ERROR)
    app.logger.addHandler(mail_handler)
    file_handler = FileHandler(app.config['STATIC_PATH']+'/logs/einfachjabber.log')
    file_handler.setLevel(logging.INFO)
    app.logger.addHandler(file_handler)

from einfachjabber.utils import *

@app.route('/')
def start():
    pagetitle = u'Jabber Tutorial Portal'
    return render_template('start.html', pagetitle=pagetitle)


@app.route('/oslist')
def oslist():
    oslist = OsCatalog().oslist()
    pagetitle = u'Jabber Tutorial Portal'
    return render_template('oslist.html', pagetitle=pagetitle, oslist=oslist)

@app.route('/reg', methods=['GET', 'POST'])
def jabberreg():
    pagetitle = u'Account Registration'
    from recaptcha.client import captcha
    captchahtml = captcha.displayhtml('6LdtjgsAAAAAAOFO0O1oFvuc_PjXicfqHD0JS3ik')
    from einfachjabber.forms import RegForm, randomserver
    form = RegForm(request.form)
    form.domain.choices = randomserver()
    if request.method == 'POST' and form.validate():
        nick = form.nick.data
        domain = form.domain.data
        email = form.email.data
        passwd = form.passwd.data
        jid = nick + '@' + domain
        subresult = captcha.submit(form.recaptcha_challenge_field.data,
                                   form.recaptcha_response_field.data,
                                   '6LdtjgsAAAAAAKoeUmTihlyU4YsC0KXpYWiP6Auy',
                                   '127.0.0.1')
        if subresult.is_valid is False:
            return render_template('jabberreg.html', form=form, success=False,
                               pagetitle=pagetitle, captchahtml=captchahtml,
                                   captchaerror=True)
        from einfachjabber.xmppreg import RegError, xmppreg
        if not app.debug:
            rr = xmppreg(nick, passwd, domain)
        else:
            rr = (1, )
        if rr[0] is 1:
            if email:
                sendmail('mailreminder', (email, jid, passwd))
            app.logger.info('New registration')
            return render_template('jabberreg.html', form=form, regerror=False,
                                   success=True, jid=jid, email=email,
                                   pagetitle=pagetitle)
        else:
            return render_template('jabberreg.html', form=form, regerror=rr[1],
                                   jid=jid, pagetitle=pagetitle,
                                   captchahtml=captchahtml)
    else:
        return render_template('jabberreg.html', form=form, success=False,
                               pagetitle=pagetitle, captchahtml=captchahtml)

@app.route('/os/<osystem>')
def clientlist(osystem):
    cl = Clients().clientlist(osystem)
    osys = OsCatalog().defclient(osystem)
    pagetitle = u'Clients für ' + osys[0]
    defaultclient = osys[1]
    return render_template('clientlist.html', pagetitle=pagetitle, clist=cl,\
                           osystem=osystem, defaultclient=defaultclient)

@app.route('/tutorial/<tid>/', defaults={'page':0})
@app.route('/tutorial/<tid>/<int:page>')
def tutorial(tid, page):
    gt = Tutorial().gettutorial(tid)
    pag = Tutorial().pagination
    metadata = {'client':gt['client'], 'clientversion':gt['clientversion'],\
                'os':gt['os']}
    pagedata = my_parser.generate(gt['tutorial'][page]['text']), gt['tutorial'][page]['image']
    maxpage = len(gt['tutorial'])-1
    pagetitle = 'Tutorial'
    flpage = pag(page, maxpage)
    osystem = tid.partition('-')[0]
    return render_template('tutorial.html', pagetitle=pagetitle, page=page,\
                           metadata=metadata, pagedata=pagedata, tid=tid,\
                           maxpage=maxpage, flpage=flpage, osystem=osystem)

@app.route('/tutorial/<tid>/links', methods=['GET', 'POST'])
def tutoriallinks(tid):
    from einfachjabber.forms import RateForm
    form = RateForm(request.form)
    form.rating.choices = [('1', u'Verbesserungswürdig'),
                           ('2', u'OK'),
                           ('3', u'Großartig!')]
    gt = Tutorial().gettutorial(tid)
    pag = Tutorial().pagination
    metadata = {'client':gt['client'], 'clientversion':gt['clientversion'],\
                'os':gt['os']}
    linkdata = gt['links']
    maxpage = len(gt['tutorial'])-1
    authordata = gt['author']
    pagetitle = 'Tutorial'
    # replace by flash please!
    success = False
    if request.method == 'POST' and form.validate():
        rating = form.rating.data
        hint = form.hint.data
        sendmail('rating', (rating, hint, tid))
        success = True

    return render_template('tutoriallinks.html', pagetitle=pagetitle,
                           metadata=metadata, linkdata=linkdata, tid=tid,
                           maxpage=maxpage, authordata=authordata,
                           paypal=app.config['PAYPAL_BUTTON'],
                           flattr=app.config['FLATTR_BUTTON'],
                           form=form, success=success)


@app.route('/tutorial/<tid>/<int:page>/more', defaults={'morepage':0})
@app.route('/tutorial/<tid>/<int:page>/more/<int:morepage>')
def tutorialmore(tid, page, morepage):
    gt = Tutorial(tid).gettutorial
    pag = Tutorial(tid).pagination
    metadata = {'client':gt['client'], 'clientversion':gt['clientversion'],\
                'os':gt['os']}
    page = page-1
    maxpage = len(gt['tutorial'][page]['more'])-1
    jumpto = gt['tutorial'][page]['jumpto']
    data = gt['tutorial'][page]['more']
    pagetitle = 'Tutorial'
    flpage = pag(morepage, maxpage)
    return render_template('more.html', pagetitle=pagetitle, data=data,\
                           metadata=metadata, maxpage=maxpage, tid=tid,\
                           morepage=morepage, page=page, flpage=flpage,\
                           jumpto=jumpto)

@app.route('/jabber')
def jabber():
    pagetitle = u'Was ist Jabber?'
    return render_template('jabber.html', pagetitle=pagetitle)

@app.route('/help')
def help():
    pagetitle = u'einfachJabber.de unterstützen'
    return render_template('help.html', pagetitle=pagetitle,
                           paypal=app.config['PAYPAL_BUTTON'],
                           flattr=app.config['FLATTR_BUTTON'])
@app.route('/impressum/')
def impressum():
    pagetitle = 'Impressum'
    return render_template('imprint.html', pagetitle=pagetitle)

@app.errorhandler(404)
def not_found(e):
    """Handles 404s"""
    pagetitle = '404 - Seite nicht gefunden'
    return render_template('404.html', pagetitle=pagetitle), 404
