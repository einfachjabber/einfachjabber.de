#!/usr/bin/python
#-*- coding: utf-8 -*-

import re
from werkzeug.exceptions import NotFound
from stepbystep.utils import expose, render_template


@expose('/')
def start(request):
    pagetitle = u'Jabber Tutorial Portal'
    return render_template('start.html', pagetitle=pagetitle)

@expose('/oslist')
def oslist(request):
    pagetitle = u'Jabber Tutorial Portal'
    return render_template('oslist.html', pagetitle=pagetitle)

@expose('/reg')
def jabberreg(request):
    pagetitle = u'Account Registration'
    from recaptcha.client import captcha
    captchahtml = captcha.displayhtml('6LeIRwsAAAAAAFM_vdWOyCyHjlGz2A4XDsw6DqcU')
    from stepbystep.forms import RegForm, composemail, randomserver
    form = RegForm(request.form)
    #print(form.recaptcha_challenge_field.data)
    #print(form.recaptcha_response_field.data)
    form.domain.choices = randomserver()
    if request.method == 'POST' and form.validate():
        nick = form.nick.data
        domain = form.domain.data
        email = form.email.data
        passwd = form.passwd.data
        jid = nick + '@' + domain
        subresult = captcha.submit(form.recaptcha_challenge_field.data,
                                   form.recaptcha_response_field.data,
                                   '6LeIRwsAAAAAAHvwuh2jEJhK_vN5oSYl_aglyky-',
                                   '127.0.0.1')
        if subresult.is_valid is False:
            return render_template('jabberreg.html', form=form, success=False,
                               pagetitle=pagetitle, captchahtml=captchahtml,
                                   captchaerror=True)
        from stepbystep.xmppreg import RegError, xmppreg
        #rr = xmppreg(nick, passwd, domain)
        rr = [1, None]
        if rr[0] is 1:
            #composemail(email, jid, passwd)
            return render_template('jabberreg.html', form=form, regerror=False,
                                   success=True, jid=jid, email=email,
                                   pagetitle=pagetitle)
        else:
            return render_template('jabberreg.html', form=form, regerror=rr[1],
                                   jid=jid, pagetitle=pagetitle)
    else:
        return render_template('jabberreg.html', form=form, success=False,
                               pagetitle=pagetitle, captchahtml=captchahtml)

@expose('/<osystem>')
def clientlist(request, osystem):
    from stepbystep.clientutils import Clients
    from stepbystep.tutorialutils import OsCatalog
    cl = Clients(osystem).clientlist
    osys = OsCatalog(osystem).defclient
    pagetitle = u'Clients für ' + osys[0]
    defaultclient = osys[1]
    return render_template('clientlist.html', pagetitle=pagetitle, clist=cl,\
                           osystem=osystem, defaultclient=defaultclient)

@expose('/tutorial/<tid>/', defaults={'page':0})
@expose('/tutorial/<tid>/<int:page>')
def tutorial(request, tid, page):
    from stepbystep.tutorialutils import Tutorial
    gt = Tutorial(tid).gettutorial
    pag = Tutorial(tid).pagination
    metadata = {'client':gt['client'], 'clientversion':gt['clientversion'],\
                'os':gt['os']}
    pagedata = gt['tutorial'][page]
    maxpage = len(gt['tutorial'])-1
    pagetitle = 'Tutorial'
    flpage = pag(page, maxpage)
    osystem = tid.partition('-')[0]
    return render_template('tutorial.html', pagetitle=pagetitle, page=page,\
                           metadata=metadata, pagedata=pagedata, tid=tid,\
                           maxpage=maxpage, flpage=flpage, osystem=osystem)

@expose('/tutorial/<tid>/links')
def tutoriallinks(request, tid):
    from stepbystep.tutorialutils import Tutorial
    gt = Tutorial(tid).gettutorial
    pag = Tutorial(tid).pagination
    metadata = {'client':gt['client'], 'clientversion':gt['clientversion'],\
                'os':gt['os']}
    linkdata = gt['links']
    maxpage = len(gt['tutorial'])-1
    authordata = gt['author']
    pagetitle = 'Tutorial'
    return render_template('tutoriallinks.html', pagetitle=pagetitle,\
                           metadata=metadata, linkdata=linkdata, tid=tid,\
                           maxpage=maxpage, authordata=authordata)


@expose('/tutorial/<tid>/<int:page>/more', defaults={'morepage':0})
@expose('/tutorial/<tid>/<int:page>/more/<int:morepage>')
def tutorialmore(request, tid, page, morepage):
    from stepbystep.tutorialutils import Tutorial
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

@expose('/impressum/')
def impressum(request):
    pagetitle = 'Impressum'
    return render_template('imprint.html', pagetitle=pagetitle)

def not_found(request):
    """Handles 404s"""
    pagetitle = '404 - Seite nicht gefunden'
    return render_template('not_found.html', pagetitle=pagetitle)

