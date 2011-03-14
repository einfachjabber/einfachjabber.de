from flask import abort, current_app, flash, g, Markup, Module, redirect, \
        render_template, request

import re

from einfachjabber.apps.admin import admin
from einfachjabber.models import OSList, TutorialDoc

@admin.route('/')
def index():
    oslist = OSList.load('oslist')
    clients = TutorialDoc.all_tutorials()

    return render_template('admin/index.html', oslist=oslist, clients=clients)

@admin.route('/clients/<osystem>')
def clientlist(osystem):
    c = re.compile(r'^'+osystem+'-')
    clients = TutorialDoc.all_tutorials()
    clients = [client for client in clients if c.match(client.id)]

    return render_template('admin/clientlist.html', clients=clients)

@admin.route('/clients/<osystem>/<client>/edit')
def client_edit(osystem, client):
    tid = '{}-{}'.format(osystem, client)
    clientDoc = TutorialDoc.load(tid)

    return render_template('admin/clientedit.html', client=clientDoc)

@admin.route('/clients/<osystem>/<client>/_setdefault')
def _client_setdefault(osystem, client):
    tid = '{}-{}'.format(osystem, client)

    clients = TutorialDoc.all_tutorials()

    for cl in clients:
        if cl['os']['short'] == osystem:
            doc = TutorialDoc.load(osystem+'-'+cl.client.short)
            if cl['client']['short'] == client:
                doc['default'] = True
            else:
                doc['default'] = False

            doc.store()

    return "Update erfolgreich!"
