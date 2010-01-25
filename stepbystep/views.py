#!/usr/bin/python
#-*- coding: utf-8 -*-

from werkzeug.exceptions import NotFound
from stepbystep.utils import expose, render_template


@expose('/')
def start(request):
    pagetitle = 'Start'
    return render_template('start.html', pagetitle=pagetitle)

@expose('/<osystem>')
def clientlist(request, osystem):
    from stepbystep.clientutils import Clients
    clients = Clients()
    clist = clients.clientlist(osystem)
    system = clients.oslist(osystem)
    pagetitle = system
    return render_template('clientlist.html', pagetitle=pagetitle, clist=clist, osystem=osystem, system=system)

@expose('/tutorial/<tid>/', defaults={'page':1})
@expose('/tutorial/<tid>/<int:page>')
def tutorial(request, tid, page):
    from stepbystep.tutorialutils import Tutorial
    tut = Tutorial()
    data = tut.gettutorial(tid)
    page = page-1
    numpages = len(data['tutorial'])-1
    pagetitle = 'Tutorial'
    flpage = 1
    if page==0:
        flpage = 0
    elif page==numpages:
        print "gleich"
        flpage = 2
    elif page>numpages:
       raise NotFound() 
    return render_template('tutorial.html', pagetitle=pagetitle, data=data, page=page, tid=tid, maxpage=numpages, flpage=flpage)

@expose('/impressum/')
def impressum(request):
    pagetitle = 'Impressum'
    return render_template('imprint.html', pagetitle=pagetitle)
