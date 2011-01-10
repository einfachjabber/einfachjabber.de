from flask import abort, current_app, flash, g, Markup, Module, redirect, \
        render_template, request
from cStringIO import StringIO
from datetime import datetime
from glob import glob
from markdown2 import markdown
from os import path
from urlparse import urljoin
from werkzeug.contrib.atom import AtomFeed
import yaml

from einfachjabber.apps.blog import blog
from einfachjabber.apps.blog.utils import *

@blog.before_request
def before_request():
    statuses = gather_statuses(path.join(current_app.config['STATUSES'] + '*.status'))
    if statuses:
        g.status = statuses[0]

@blog.route('/')
def list_posts():
    posts, postkeys = gather_posts(path.join(current_app.config['POSTS'] + '*.mkd'))
    for key in postkeys:
        datestring = str(posts[key]['date'])[0:10]
        posts[key]['date'] = '%s.%s.%s' % (datestring[8:10],
                                           datestring[5:7],
                                           datestring[0:4])
    return render_template('blog/posts.html', posts=posts, postkeys=postkeys)

@blog.route('/<postslug>')
def post(postslug):
    filename = postslug + '.mkd'
    filepath = current_app.config['POSTS'] + filename
    metadata, text = parse_postfile(filepath)
    postslug, post = assemble_post(filename, metadata, text)
    datestring = str(post['date'])[0:10]
    post['date'] = '%s.%s.%s' % (datestring[8:10],
                                 datestring[5:7],
                                 datestring[0:4])
    return render_template('blog/single.html', post=post, postslug=postslug)

@blog.route('/recent.atom')
def recent_feed():
    feed = AtomFeed('blog.einfachjabber.de - Feed',
                    feed_url=request.url, url=request.url_root)
    posts, postkeys = gather_posts(path.join(current_app.config['POSTS'] + '*.mkd'))
    print postkeys
    counter = 0
    for key in postkeys:
        if counter < 10:
            feed.add(posts[key]['title'], unicode(posts[key]['text']),
                content_type='html',
                author=posts[key]['author'],
                url=make_external(key),
                updated=posts[key]['date'])
            counter += 1
    return feed.get_response()

@blog.route('/status')
def status():
    statuses = gather_statuses(path.join(current_app.config['STATUSES'] + '*.status'))
    if not statuses:
        statuses = [{'text': 'No status set'}]
    return render_template('blog/status.html', statuses=statuses)

@blog.route('/status/update', methods=['GET', 'POST'])
def status_update():
    if request.method == 'POST':
        now = datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ')
        filename = current_app.config['STATUSES'] + now + '.status'
        if request.form['password'] == current_app.config['PASSWORD']:
            if request.form['status']:
                print request.form['status'], now
                f = open(filename, 'w')
                f.write(now + '\n'
                        + '%s' % request.form['indicator'] + '\n'
                        + '%s' % request.form['status'])
                f.close()
                flash('Status wurde gesetzt.', 'info')
                return redirect('status')
        else:
            flash('Falsches Passwort!', 'error')
    return render_template('blog/statusupdate.html')

@blog.route('/status.atom')
def status_feed():
    feed = AtomFeed('einfachjabber.de - Server-Status-Feed',
                    feed_url=request.url, url=request.url_root,
                    subtitle='Alle Zeiten sind UTC. All times are UTC.')
    statuses = gather_statuses(path.join(current_app.config['STATUSES'] + '*.status'))
    counter = 0
    for status in statuses:
        if counter < 10:
            feed.add(unicode(status['text']),
                content_type='html',
                author='einfachjabber Statusfeed',
                url=make_external(''),
                updated=status['date'])
            counter += 1
    return feed.get_response()
