from flask import abort, Markup, Module, render_template, request
from cStringIO import StringIO
from datetime import datetime
from glob import glob
from markdown2 import markdown
from os import path
from urlparse import urljoin
from werkzeug.contrib.atom import AtomFeed
import yaml

def extract_date(filename):
    datestring = path.split(filename)[-1][0:10]
    return datetime.strptime(datestring, '%Y-%m-%d')

def extract_datetime(datestring):
    return datetime.strptime(datestring.strip(), '%Y-%m-%dT%H:%M:%SZ')

def parse_postfile(filename):
    filehead = 0
    yamldoc = ''
    tempfile = StringIO()
    yamllist = []
    try:
        f = open(filename, 'r')
    except:
        abort(404)
    for line in f.readlines():
        if line.strip() == '---':
            if not filehead:
                filehead = 1
            else:
                filehead = 0
                continue
        if filehead:
            yamllist.append(line)
            yamldoc = '\n'.join(yamllist)
        else:
            tempfile.write(line)
    metadata = yaml.load(yamldoc)
    text = markdown(tempfile.getvalue(), extras=['code-color', 'code-friendly'])
    tempfile.close()
    return metadata, text

def assemble_post(filename, metadata, text):
    postslug = path.split(filename)[-1][0:-4]
    post = {}
    post['date'] = extract_date(filename)
    post['title'] = metadata['title']
    post['author'] = metadata['author']
    post['email'] = metadata['email']
    post['jabber'] = metadata['jabber']
    post['text'] = Markup(text)
    return postslug, post

def gather_posts(postpath):
    posts = {}
    for filename in glob(postpath):
        metadata, text = parse_postfile(filename)
        postslug, post = assemble_post(filename, metadata, text)
        posts[postslug] = post
    postkeys = posts.keys()
    postkeys.sort(reverse=True)
    return posts, postkeys

def parse_statusfile(filename):
    try:
        f = open(filename, 'r')
    except:
        abort(404)
    date = f.readline()
    indicator = f.readline()
    text = f.readline()
    return date, indicator, text

def assemble_statuses(date, indicator, text):
    status = {}
    status['date'] = extract_datetime(date)
    status['indicator'] = indicator
    status['text'] = text
    return status

def gather_statuses(statuspath):
    statuses = []
    for filename in glob(statuspath):
        date, indicator, text = parse_statusfile(filename)
        status = assemble_statuses(date, indicator, text)
        statuses.append(status)
    statuses.sort(reverse=True)
    return statuses

def make_external(url):
    return urljoin(request.url_root, '/blog/' + url)
