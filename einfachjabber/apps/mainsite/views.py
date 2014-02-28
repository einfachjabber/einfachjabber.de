# -*- coding: utf-8 -*-
import re
from flask import request, redirect, url_for, abort, render_template, flash, \
        current_app
from einfachjabber.utils import *
from einfachjabber.apps.mainsite import mainsite
from einfachjabber.models import OSList, TutorialDoc


# Bad hard redirect, has to do for now
@mainsite.route('/blog')
def blog_redirect():
    return redirect('http://www.einfachjabber.de/blog/')

@mainsite.route('/')
def start():
    pagetitle = u'Jabber Tutorial Portal'
    return render_template('mainsite/start.html', pagetitle=pagetitle)

@mainsite.route('/oslist')
def oslist():
    oslist = OSList.load('oslist')
    pagetitle = u'Bitte wähle dein Betriebssystem'
    return render_template('mainsite/oslist.html', pagetitle=pagetitle,
                                oslist=oslist['data'])

@mainsite.route('/os/<osystem>')
def clientlist(osystem):
    c = re.compile(r'^'+osystem+'-')
    clients = TutorialDoc.all_tutorials()
    clist = [ client for client in clients if c.match(client.id) ]

    return render_template('mainsite/clientlist.html', clist=clist)

@mainsite.route('/tutorial/<tid>/', defaults={'page':0})
@mainsite.route('/tutorial/<tid>/<int:page>')
def tutorial(tid, page):
    gt = TutorialDoc.load(tid)
    pag = Tutorial().pagination
    metadata = {
        'client':gt['client'],
        'clientversion':gt['clientversion'],
        'os':gt['os']
    }
    pagedata = gt['tutorial'][page]['text'], gt['tutorial'][page]['image']
    maxpage = len(gt['tutorial'])-1
    pagetitle = 'Tutorial'
    flpage = pag(page, maxpage)
    osystem = tid.partition('-')[0]
    return render_template('mainsite/tutorial.html', pagetitle=pagetitle,
                           page=page, metadata=metadata, pagedata=pagedata,
                           tid=tid, maxpage=maxpage, flpage=flpage,
                           osystem=osystem)

@mainsite.route('/tutorial/<tid>/links', methods=['GET', 'POST'])
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

    return render_template('mainsite/tutoriallinks.html', pagetitle=pagetitle,
                           metadata=metadata, linkdata=linkdata, tid=tid,
                           maxpage=maxpage, authordata=authordata,
                           paypal=current_app.config['PAYPAL_BUTTON'],
                           flattr=current_app.config['FLATTR_BUTTON'],
                           form=form, success=success)


@mainsite.route('/tutorial/<tid>/<int:page>/more', defaults={'morepage':0})
@mainsite.route('/tutorial/<tid>/<int:page>/more/<int:morepage>')
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
    return render_template('mainsite/more.html', pagetitle=pagetitle,
                           data=data, metadata=metadata, maxpage=maxpage,
                           tid=tid, morepage=morepage, page=page,
                           flpage=flpage, jumpto=jumpto)

@mainsite.route('/reg', methods=['GET', 'POST'])
def jabberreg():
    pagetitle = u'Account Registration'
    from einfachjabber.forms import RegForm, randomserver
    form = RegForm(request.form)
    form.domain.choices = randomserver()
    if request.method == 'POST' and form.validate():
        nick = form.nick.data
        domain = form.domain.data
        email = form.email.data
        passwd = form.passwd.data
        jid = nick + '@' + domain
        from einfachjabber.xmppreg import RegError, xmppreg
        #if not current_app.debug:
        rr = xmppreg(nick, passwd, domain)
        #else:
        #    rr = (1, )
        if rr[0] is 1:
            if email:
                sendmail('mailreminder', (email, jid, passwd))
            current_app.logger.info('New registration')
            return render_template('mainsite/jabberreg.html', form=form,
                                   regerror=False, success=True, jid=jid,
                                   email=email, pagetitle=pagetitle)
        else:
            return render_template('mainsite/jabberreg.html', form=form,
                                   regerror=rr[1], jid=jid,
                                   pagetitle=pagetitle)
    else:
        return render_template('mainsite/jabberreg.html', form=form,
                               success=False, pagetitle=pagetitle)

@mainsite.route('/jabber')
def jabber():
    pagetitle = u'Was ist Jabber?'
    return render_template('mainsite/jabber.html', pagetitle=pagetitle)

@mainsite.route('/help')
def help():
    pagetitle = u'einfachJabber.de unterstützen'
    return render_template('mainsite/help.html', pagetitle=pagetitle,
                           paypal=current_app.config['PAYPAL_BUTTON'],
                           flattr=current_app.config['FLATTR_BUTTON'])
@mainsite.route('/impressum')
def impressum():
    pagetitle = 'Impressum'
    return render_template('mainsite/imprint.html', pagetitle=pagetitle)
