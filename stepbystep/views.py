#!/usr/bin/python
#-*- coding: utf-8 -*-

import re
from werkzeug.exceptions import NotFound
from stepbystep.utils import expose, render_template


@expose('/')
def start(request):
    pagetitle = u'Jabber Tutorial Portal'
    return render_template('start.html', pagetitle=pagetitle)

@expose('/<osystem>')
def clientlist(request, osystem):
    from stepbystep.clientutils import Clients
    cl = Clients(osystem).clientlist
    osys = Clients(osystem).oslist
    pagetitle = u'Clients für ' + osys[0]
    defaultclient = osys[1]
    return render_template('clientlist.html', pagetitle=pagetitle, clist=cl, osystem=osystem, defaultclient=defaultclient)

@expose('/tutorial/<tid>/', defaults={'page':0})
@expose('/tutorial/<tid>/<int:page>')
def tutorial(request, tid, page):
    from stepbystep.tutorialutils import Tutorial
    gt = Tutorial(tid).gettutorial
    pag = Tutorial(tid).pagination
    metadata = {'client':gt['client'], 'clientversion':gt['clientversion'], 'os':gt['os']}
    pagedata = gt['tutorial'][page]
    maxpage = len(gt['tutorial'])-1
    pagetitle = 'Tutorial'
    flpage = pag(page, maxpage)
    osystem = tid.partition('-')[0]
    return render_template('tutorial.html', pagetitle=pagetitle, metadata=metadata, pagedata=pagedata, page=page, tid=tid, maxpage=maxpage, flpage=flpage, osystem=osystem)

@expose('/tutorial/<tid>/links')
def tutoriallinks(request, tid):
    from stepbystep.tutorialutils import Tutorial
    gt = Tutorial(tid).gettutorial
    pag = Tutorial(tid).pagination
    metadata = {'client':gt['client'], 'clientversion':gt['clientversion'], 'os':gt['os']}
    linkdata = gt['links']
    maxpage = len(gt['tutorial'])-1
    pagetitle = 'Tutorial'
    return render_template('tutoriallinks.html', pagetitle=pagetitle, metadata=metadata, linkdata=linkdata, tid=tid, maxpage=maxpage)


@expose('/tutorial/<tid>/<int:page>/more', defaults={'morepage':0})
@expose('/tutorial/<tid>/<int:page>/more/<int:morepage>')
def tutorialmore(request, tid, page, morepage):
    from stepbystep.tutorialutils import Tutorial
    gt = Tutorial(tid).gettutorial
    pag = Tutorial(tid).pagination
    metadata = {'client':gt['client'], 'clientversion':gt['clientversion'], 'os':gt['os']}
    page = page-1
    maxpage = len(gt['tutorial'][page]['more'])-1
    moredata = gt['tutorial'][page]['more']
    jumpto = gt['tutorial'][page]['jumpto']
    data = gt['tutorial'][page]['more']
    pagetitle = 'Tutorial'
    flpage = pag(morepage, maxpage)
    return render_template('more.html', pagetitle=pagetitle, data=data, metadata=metadata, moredata=moredata, maxpage=maxpage, tid=tid, morepage=morepage, page=page, flpage=flpage, jumpto=jumpto)

@expose('/impressum/')
def impressum(request):
    pagetitle = 'Impressum'
    return render_template('imprint.html', pagetitle=pagetitle)

def not_found(request):
    """Handles 404s"""
    pagetitle = '404 - Seite nicht gefunden'
    return render_template('not_found.html', pagetitle=pagetitle)

