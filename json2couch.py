from couchdb.client import Server
from glob import glob
from os import path
import json
import re

DB_SERVER = 'http://ben:42ph.74rgt@192.168.103.100:5984'
DB_NAME = 'einfachjabber'
DB_REMOTE = 'http://ben:42ph.74rgt@192.168.103.30:5984/einfachjabber'

server = Server(url=DB_SERVER)
server.delete(DB_NAME)
db = server.create(DB_NAME)

def defclient(osystem):
    """
    Maps the OS short-names to their long pendants
    and their default client
    """

    system = ''
    if osystem == 'android':
        system = ['Android', 'beem']
    if osystem == 'blackberry':
        system = ['Blackberry', 'None']
    if osystem == 'debian':
        system = ['Debian', 'pidgin']
    if osystem == 'fedora':
        system = ['Fedora', 'empathy']
    if osystem == 'iphone':
        system = ['iPhone', 'None']
    if osystem == 'jolicloud':
        system = ['Jolicloud', 'pidgin']
    if osystem == 'kubuntu':
        system = ['Kubuntu', 'kopete']
    if osystem == 'macosx':
        system = ['Mac OS X', 'ichat']
    if osystem == 'maemo2008':
        system = ['Maemo OS2008', 'pidgin']
    if osystem == 'opensolaris':
        system = ['OpenSolaris', 'pidgin']
    if osystem == 'opensuse':
        system = ['OpenSUSE', 'kopete']
    if osystem == 'pcbsd':
        system = ['PC BSD', 'pidgin']
    if osystem == 'ubuntu':
        system = ['Ubuntu', 'empathy']
    if osystem == 'ubuntunbe':
        system = ['Ubuntu Netbook Edition', 'empathy']
    if osystem == 'webchat':
        system = ['Webchat', 'meebo']
    if osystem == 'win7':
        system = ['Windows Vista / 7', 'pidgin']
    if osystem == 'winxp':
        system = ['Windows XP', 'pidgin']
    return system

def oslist():
    """builds the menu for /os"""
    doc = {
        'data': {
            'Linux': [
                    { 'name': 'Debian', 'short': 'debian' },
                    { 'name': 'Fedora', 'short': 'fedora' },
                    { 'name': 'Kubuntu', 'short': 'kubuntu' },
                    { 'name': 'OpenSUSE', 'short': 'opensuse' },
                    { 'name': 'Ubuntu', 'short': 'ubuntu' },
                    { 'name': 'Ubuntu Netbook Edition', 'short': 'ubuntunbe' },
                    { 'name': 'Jolicloud', 'short': 'jolicloud' },
                    ],
            'MacOSX': [],
            'Windows': [
                    { 'name': 'Windows Vista / 7', 'short': 'win7'},
                    { 'name': 'Windows XP', 'short': 'winxp' }
                   ],
            'Mobil': [
                    { 'name': 'Android', 'short': 'android' },
                    { 'name': 'Blackberry', 'short': 'blackberry'},
                    { 'name': 'iPhone', 'short': 'iphone' },
                    { 'name': 'Maemo2008', 'short': 'maemo2008'},
                   ],
            'Andere': [
                    { 'name': 'OpenSolaris', 'short': 'opensolaris'},
                    { 'name': 'PC BSD', 'short': 'pcbsd' }
                   ],
        }
    }
    doc['_id'] = 'oslist'
    doc['doctype'] = 'oslist'
    db.save(doc)

def j2c():
    tutorials = {}
    for filename in glob('einfachjabber.de-data/_tutorials/*.json'):
        tid = path.split(filename)[-1][:-5]

        with open(filename, 'r') as f:
            try:
                doc = json.load(f)
            except:
                print 'error loading json-data from {}'.format(tid)

        for item in doc['tutorial']:
            # replace quotation-marks by **
            item['text'] = item['text'].replace('"','**')

            # replace wiki-markup by markdown
            re1='.*?'
            re2='(\\[.*?\\]\\])'
            rg = re.compile(re1+re2,re.IGNORECASE|re.DOTALL)
            m = rg.search(item['text'])
            if m:
                sbraces = m.group(1)
                sbraces_raw = sbraces.replace('[[','').replace(']]','')
                if '|' in sbraces:
                    sbraces_raw = sbraces_raw.split('|')
                    rest_link = '[{}]({})'.format(sbraces_raw[1],
                                                  sbraces_raw[0])
                else:
                    rest_link = '[{}]({})'.format(sbraces_raw, sbraces_raw)

                item['text'] = item['text'].replace(sbraces,
                        rest_link).replace('[[','').replace(']]', '')

        # get os and client from tid
        os, cl = tid.split('-')

        # set default client information
        if defclient(os)[1] == cl:
            doc['default'] = True
        else:
            doc['default'] = False

        # amend short form to os-field
        doc_os = {
                'full': doc['os'],
                'short': os
             }
        doc['os'] = doc_os

        # amend short form to client-field
        doc_cl = {
                'full': doc['client'],
                'short': cl
             }
        doc['client'] = doc_cl

        # set document id to tid
        doc['_id'] = tid
        doc['doc_type'] = 'tutorial'
        db.save(doc)


if __name__ == '__main__':
    j2c()
    oslist()
    server.replicate(DB_NAME, DB_REMOTE)
