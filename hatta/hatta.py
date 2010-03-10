#!/usr/bin/env python
# -*- coding: utf-8 -*-

# @copyright: 2008-2009 Radomir Dopieralski <hatta@sheep.art.pl>
# @license: GNU GPL, see COPYING for details.

"""
Hatta Wiki is a wiki engine designed to be used with Mercurial repositories.
It requires Mercurial and Werkzeug python modules.

Hatta's pages are just plain text files (and also images, binaries, etc.) in
some directory in your repository. For example, you can put it in your
project's "docs" directory to keep documentation. The files can be edited both
from the wiki or with a text editor -- in either case the changes committed to
the repository will appear in the recent changes and in page's history.

See hatta.py --help for usage.
"""

import base64
import datetime
import difflib
import gettext
import itertools
import mimetypes
import os
import re
import sqlite3
import sys
import tempfile
import thread
import unicodedata


# Avoid WSGI errors, see http://mercurial.selenic.com/bts/issue1095
sys.stdout = sys.__stdout__
sys.stderr = sys.__stderr__

import werkzeug
import werkzeug.exceptions
import werkzeug.routing

try:
    import Image
except ImportError:
    Image = None

try:
    import pygments
    import pygments.util
    import pygments.lexers
    import pygments.formatters
    import pygments.styles
except ImportError:
    pygments = None

# Note: we have to set these before importing Mercurial
os.environ['HGENCODING'] = 'utf-8'
os.environ['HGMERGE'] = "internal:merge"

import mercurial.hg
import mercurial.ui
import mercurial.revlog
import mercurial.util
import mercurial.hgweb

__version__ = '1.3.3dev'
name = 'Hatta'
url = 'http://hatta-wiki.org/'
description = 'Wiki engine that lives in Mercurial repository.'

mimetypes.add_type('application/x-python', '.wsgi')
mimetypes.add_type('application/x-javascript', '.js')
mimetypes.add_type('text/x-rst', '.rst')


def external_link(addr):
    """
    Decide whether a link is absolute or internal.

    >>> external_link('http://example.com')
    True
    >>> external_link('https://example.com')
    True
    >>> external_link('ftp://example.com')
    True
    >>> external_link('mailto:user@example.com')
    True
    >>> external_link('PageTitle')
    False
    >>> external_link(u'ąęśćUnicodePage')
    False

    """

    return (addr.startswith('http://')
            or addr.startswith('https://')
            or addr.startswith('ftp://')
            or addr.startswith('mailto:'))

def page_mime(title):
    """
    Guess page's mime type ased on corresponding file name.
    Default ot text/x-wiki for files without an extension.

    >>> page_mime(u'something.txt')
    'text/plain'
    >>> page_mime(u'SomePage')
    'text/x-wiki'
    >>> page_mime(u'ąęśUnicodePage')
    'text/x-wiki'
    >>> page_mime(u'image.png')
    'image/png'
    >>> page_mime(u'style.css')
    'text/css'
    >>> page_mime(u'archive.tar.gz')
    'archive/gzip'
    """

    addr = title.encode('utf-8') # the encoding doesn't relly matter here
    mime, encoding = mimetypes.guess_type(addr, strict=False)
    if encoding:
        mime = 'archive/%s' % encoding
    if mime is None:
        mime = 'text/x-wiki'
    return mime


class WikiError(werkzeug.exceptions.HTTPException):
    """Base class for all error pages."""


class ForbiddenErr(WikiError):
    code = 403


class NotFoundErr(WikiError):
    code = 404


class UnsupportedMediaTypeErr(WikiError):
    code = 415


class NotImplementedErr(WikiError):
    code = 501


class ServiceUnavailableErr(WikiError):
    code = 503


class WikiConfig(object):
    """
    Responsible for reading and storing site configuration. Contains the
    default settings.

    >>> config = WikiConfig(port='2080')
    >>> config.sanitize()
    >>> config.get('port')
    2080
    """

    default_filename = u'hatta.conf'

    # Please see the bottom of the script for modifying these values.

    def __init__(self, **kw):
        self.config = dict(kw)
        self.parse_environ()

    def sanitize(self):
        """
        Convert options to their required types.
        """

        try:
            self.config['port'] = int(self.get('port', 0))
        except ValueError:
            self.config['port'] = 8080

    def parse_environ(self):
        """Check the environment variables for options."""

        prefix = 'HATTA_'
        for key, value in os.environ.iteritems():
            if key.startswith(prefix):
                name = key[len(prefix):].lower()
                self.config[name] = value

    def parse_args(self):
        """Check the commandline arguments for options."""

        import optparse

        self.options = []
        parser = optparse.OptionParser()

        def add(*args, **kw):
            self.options.append(kw['dest'])
            parser.add_option(*args, **kw)

        add('-V', '--version', dest='show_version', default=False,
            help='Display version and exit', action="store_true")
        add('-d', '--pages-dir', dest='pages_path',
            help='Store pages in DIR', metavar='DIR')
        add('-t', '--cache-dir', dest='cache_path',
            help='Store cache in DIR', metavar='DIR')
        add('-i', '--interface', dest='interface',
            help='Listen on interface INT', metavar='INT')
        add('-p', '--port', dest='port', type='int',
            help='Listen on port PORT', metavar='PORT')
        add('-s', '--script-name', dest='script_name',
            help='Override SCRIPT_NAME to NAME', metavar='NAME')
        add('-n', '--site-name', dest='site_name',
            help='Set the name of the site to NAME', metavar='NAME')
        add('-m', '--front-page', dest='front_page',
            help='Use PAGE as the front page', metavar='PAGE')
        add('-e', '--encoding', dest='page_charset',
            help='Use encoding ENC to read and write pages', metavar='ENC')
        add('-c', '--config-file', dest='config_file',
            help='Read configuration from FILE', metavar='FILE')
        add('-l', '--language', dest='language',
            help='Translate interface to LANG', metavar='LANG')
        add('-r', '--read-only', dest='read_only',
            help='Whether the wiki should be read-only', action="store_true")
        add('-g', '--icon-page', dest='icon_page', metavar="PAGE",
            help='Read icons graphics from PAGE.')
        add('-w', '--hgweb', dest='hgweb',
            help='Enable hgweb access to the repository', action="store_true")
        add('-W', '--wiki-words', dest='wiki_words',
            help='Enable WikiWord links', action="store_true")
        add('-I', '--ignore-indent', dest='ignore_indent',
            help='Treat indented lines as normal text', action="store_true")
        add('-P', '--pygments-style', dest='pygments_style',
            help='Use the STYLE pygments style for highlighting',
            metavar='STYLE')
        add('-D', '--subdirectories', dest='subdirectories',
            action="store_true",
            help='Store subpages as subdirectories in the filesystem')

        options, args = parser.parse_args()
        for option, value in options.__dict__.iteritems():
            if option in self.options:
                if value is not None:
                    self.config[option] = value

    def parse_files(self, files=None):
        """Check the config files for options."""

        import ConfigParser

        if files is None:
            files = [self.get('config_file', self.default_filename)]
        parser = ConfigParser.SafeConfigParser()
        parser.read(files)
        for section in parser.sections():
            for option, value in parser.items(section):
                self.config[option] = value

    def save_config(self, filename=None):
        """Saves configuration to a given file."""
        if filename is None:
            filename = self.default_filename

        import ConfigParser
        parser = ConfigParser.RawConfigParser()
        section = self.config['site_name']
        parser.add_section(section)
        for key, value in self.config.iteritems():
            parser.set(section, str(key), str(value))

        configfile = open(filename, 'wb')
        try:
            parser.write(configfile)
        finally:
            configfile.close()

    def get(self, option, default_value=None):
        """
        Get the value of a config option or default if not set.

        >>> config = WikiConfig(option=4)
        >>> config.get("ziew", 3)
        3
        >>> config.get("ziew")
        >>> config.get("ziew", "ziew")
        'ziew'
        >>> config.get("option")
        4
        """

        return self.config.get(option, default_value)

    def get_bool(self, option, default_value=False):
        """
        Like get, only convert the value to True or False.
        """

        value = self.get(option, default_value)
        if value in (
            1, True,
            'True', 'true', 'TRUE',
            '1',
            'on', 'On', 'ON',
            'yes', 'Yes', 'YES',
            'enable', 'Enable', 'ENABLE',
            'enabled', 'Enabled', 'ENABLED',
        ):
            return True
        elif value in (
            None, 0, False,
            'False', 'false', 'FALSE',
            '0',
            'off', 'Off', 'OFF',
            'no', 'No', 'NO',
            'disable', 'Disable', 'DISABLE',
            'disabled', 'Disabled', 'DISABLED',
        ):
            return False
        else:
            raise ValueError("expected boolean value")

    def set(self, key, value):
        self.config[key] = value


def locked_repo(func):
    """A decorator for locking the repository when calling a method."""

    def new_func(self, *args, **kwargs):
        """Wrap the original function in locks."""

        wlock = self.repo.wlock()
        lock = self.repo.lock()
        try:
            func(self, *args, **kwargs)
        finally:
            lock.release()
            wlock.release()

    return new_func

class WikiStorage(object):
    """
    Provides means of storing wiki pages and keeping track of their
    change history, using Mercurial repository as the storage method.
    """

    def __init__(self, path, charset=None):
        """
        Takes the path to the directory where the pages are to be kept.
        If the directory doen't exist, it will be created. If it's inside
        a Mercurial repository, that repository will be used, otherwise
        a new repository will be created in it.
        """

        self.charset = charset or 'utf-8'
        self.path = os.path.abspath(path)
        if not os.path.exists(self.path):
            os.makedirs(self.path)
        self.repo_path = self._find_repo_path(self.path)
        try:
            self.ui = mercurial.ui.ui(report_untrusted=False,
                                      interactive=False, quiet=True)
        except TypeError:
            # Mercurial 1.3 changed the way we setup the ui object.
            self.ui = mercurial.ui.ui()
            self.ui.quiet = True
            self.ui._report_untrusted = False
            self.ui.setconfig('ui', 'interactive', False)
        if self.repo_path is None:
            self.repo_path = self.path
            create = True
        else:
            create = False
        self.repo_prefix = self.path[len(self.repo_path):].strip('/')
        self._repos = {}
        # Create the repository if needed.
        mercurial.hg.repository(self.ui, self.repo_path, create=create)

    def reopen(self):
        """Close and reopen the repo, to make sure we are up to date."""

        #self.repo = mercurial.hg.repository(self.ui, self.repo_path)
        self._repos = {}

    @property
    def repo(self):
        """Keep one open repository per thread."""

        thread_id = thread.get_ident()
        try:
            return self._repos[thread_id]
        except KeyError:
            repo = mercurial.hg.repository(self.ui, self.repo_path)
            self._repos[thread_id] = repo
            return repo

    def _find_repo_path(self, path):
        """Go up the directory tree looking for a repository."""

        while not os.path.isdir(os.path.join(path, ".hg")):
            old_path, path = path, os.path.dirname(path)
            if path == old_path:
                return None
        return path

    def _check_path(self, path):
        """
        Ensure that the path is within allowed bounds.
        """

        abspath = os.path.abspath(path)
        if os.path.islink(path) or os.path.isdir(path):
            raise ForbiddenErr(
                _(u"Can't use symbolic links or directories as pages"))
        if not abspath.startswith(self.path):
            raise ForbiddenErr(
                _(u"Can't read or write outside of the pages repository"))

    def _file_path(self, title):
        return os.path.join(self.repo_path, self._title_to_file(title))

    def _title_to_file(self, title):
        title = unicode(title).strip()
        filename = werkzeug.url_quote(title, safe='')
        # Escape special windows filenames and dot files
        _windows_device_files = ('CON', 'AUX', 'COM1', 'COM2', 'COM3',
                                 'COM4', 'LPT1', 'LPT2', 'LPT3', 'PRN',
                                 'NUL')
        if (filename.split('.')[0].upper() in _windows_device_files or
            filename.startswith('_') or filename.startswith('.')):
            filename = '_' + filename
        return os.path.join(self.repo_prefix, filename)

    def _file_to_title(self, filepath):
        if not filepath.startswith(self.repo_prefix):
            raise ForbiddenErr(
                _(u"Can't read or write outside of the pages repository"))
        name = filepath[len(self.repo_prefix):].strip('/')
        # Unescape special windows filenames and dot files
        if name.startswith('_') and len(name)>1:
            name = name[1:]
        return werkzeug.url_unquote(name)

    def __contains__(self, title):
        if title:
            file_path = self._file_path(title)
            return os.path.isfile(file_path) and not os.path.islink(file_path)

    def __iter__(self):
        return self.all_pages()

    def merge_changes(self, changectx, repo_file, text, user, parent):
        """Commits and merges conflicting changes in the repository."""

        tip_node = changectx.node()
        filectx = changectx[repo_file].filectx(parent)
        parent_node = filectx.changectx().node()

        self.repo.dirstate.setparents(parent_node)
        node = self._commit([repo_file], text, user)

        partial = lambda filename: repo_file == filename
        try:
            unresolved = mercurial.merge.update(self.repo, tip_node,
                                                True, True, partial)
            msg = _(u'merge of edit conflict')
        except mercurial.util.Abort:
            unresolved = 1, 1, 1, 1
            msg = _(u'failed merge of edit conflict')
        self.repo.dirstate.setparents(tip_node, node)
        # Mercurial 1.1 and later need updating the merge state
        try:
            mercurial.merge.mergestate(self.repo).mark(repo_file, "r")
        except (AttributeError, KeyError):
            pass
        return msg

    @locked_repo
    def save_file(self, title, file_name, author=u'', comment=u'', parent=None):
        """Save an existing file as specified page."""

        user = author.encode('utf-8') or _(u'anon').encode('utf-8')
        text = comment.encode('utf-8') or _(u'comment').encode('utf-8')
        repo_file = self._title_to_file(title)
        file_path = self._file_path(title)
        self._check_path(file_path)
        mercurial.util.rename(file_name, file_path)
        changectx = self._changectx()
        try:
            filectx_tip = changectx[repo_file]
            current_page_rev = filectx_tip.filerev()
        except mercurial.revlog.LookupError:
            self.repo.add([repo_file])
            current_page_rev = -1
        if parent is not None and current_page_rev != parent:
            msg = self.merge_changes(changectx, repo_file, text, user, parent)
            user = '<wiki>'
            text = msg.encode('utf-8')
        self._commit([repo_file], text, user)


    def _commit(self, files, text, user):
        try:
            return self.repo.commit(files=files, text=text, user=user,
                                    force=True, empty_ok=True)
        except TypeError:
            # Mercurial 1.3 doesn't accept empty_ok or files parameter
            match = mercurial.match.exact(self.repo_path, '', list(files))
            return self.repo.commit(match=match, text=text, user=user,
                                    force=True)


    def save_data(self, title, data, author=u'', comment=u'', parent=None):
        """Save data as specified page."""

        try:
            temp_path = tempfile.mkdtemp(dir=self.path)
            file_path = os.path.join(temp_path, 'saved')
            f = open(file_path, "wb")
            f.write(data)
            f.close()
            self.save_file(title, file_path, author, comment, parent)
        finally:
            try:
                os.unlink(file_path)
            except OSError:
                pass
            try:
                os.rmdir(temp_path)
            except OSError:
                pass

    def save_text(self, title, text, author=u'', comment=u'', parent=None):
        """Save text as specified page, encoded to charset."""

        data = text.encode(self.charset)
        self.save_data(title, data, author, comment, parent)

    def page_text(self, title):
        """Read unicode text of a page."""

        data = self.open_page(title).read()
        text = unicode(data, self.charset, 'replace')
        return text

    def page_lines(self, page):
        for data in page.xreadlines():
            yield unicode(data, self.charset, 'replace')

    @locked_repo
    def delete_page(self, title, author=u'', comment=u''):
        user = author.encode('utf-8') or 'anon'
        text = comment.encode('utf-8') or 'deleted'
        repo_file = self._title_to_file(title)
        file_path = self._file_path(title)
        self._check_path(file_path)
        try:
            os.unlink(file_path)
        except OSError:
            pass
        self.repo.remove([repo_file])
        self._commit([repo_file], text, user)

    def open_page(self, title):
        """Open the page and return a file-like object with its contents."""

        file_path = self._file_path(title)
        self._check_path(file_path)
        try:
            return open(file_path, "rb")
        except IOError:
            raise NotFoundErr()

    def page_file_meta(self, title):
        """Get page's inode number, size and last modification time."""

        try:
            (st_mode, st_ino, st_dev, st_nlink, st_uid, st_gid, st_size,
             st_atime, st_mtime, st_ctime) = os.stat(self._file_path(title))
        except OSError:
            return 0, 0, 0
        return st_ino, st_size, st_mtime

    def page_meta(self, title):
        """Get page's revision, date, last editor and his edit comment."""

        filectx_tip = self._find_filectx(title)
        if filectx_tip is None:
            raise NotFoundErr()
            #return -1, None, u'', u''
        rev = filectx_tip.filerev()
        filectx = filectx_tip.filectx(rev)
        date = datetime.datetime.fromtimestamp(filectx.date()[0])
        author = unicode(filectx.user(), "utf-8",
                         'replace').split('<')[0].strip()
        comment = unicode(filectx.description(), "utf-8", 'replace')
        return rev, date, author, comment

    def repo_revision(self):
        """Give the latest revision of the repository."""

        return self._changectx().rev()


    def _changectx(self):
        """Get the changectx of the tip."""

        try:
            # This is for Mercurial 1.0
            return self.repo.changectx()
        except TypeError:
            # Mercurial 1.3 (and possibly earlier) needs an argument
            return self.repo.changectx('tip')

    def _find_filectx(self, title):
        """Find the last revision in which the file existed."""

        repo_file = self._title_to_file(title)
        changectx = self._changectx()
        stack = [changectx]
        while repo_file not in changectx:
            if not stack:
                return None
            changectx = stack.pop()
            for parent in changectx.parents():
                if parent != changectx:
                    stack.append(parent)
        return changectx[repo_file]

    def page_history(self, title):
        """Iterate over the page's history."""

        filectx_tip = self._find_filectx(title)
        if filectx_tip is None:
            return
        maxrev = filectx_tip.filerev()
        minrev = 0
        for rev in range(maxrev, minrev-1, -1):
            filectx = filectx_tip.filectx(rev)
            date = datetime.datetime.fromtimestamp(filectx.date()[0])
            author = unicode(filectx.user(), "utf-8",
                             'replace').split('<')[0].strip()
            comment = unicode(filectx.description(), "utf-8", 'replace')
            yield rev, date, author, comment

    def page_revision(self, title, rev):
        """Get binary content of the specified revision of the page."""

        filectx_tip = self._find_filectx(title)
        if filectx_tip is None:
            raise NotFoundErr()
        try:
            data = filectx_tip.filectx(rev).data()
        except IndexError:
            raise NotFoundErr()
        return data

    def revision_text(self, title, rev):
        """Get unicode text of the specified revision of the page."""

        data = self.page_revision(title, rev)
        text = unicode(data, self.charset, 'replace')
        return text

    def history(self):
        """Iterate over the history of entire wiki."""

        changectx = self._changectx()
        maxrev = changectx.rev()
        minrev = 0
        for wiki_rev in range(maxrev, minrev-1, -1):
            change = self.repo.changectx(wiki_rev)
            date = datetime.datetime.fromtimestamp(change.date()[0])
            author = unicode(change.user(), "utf-8",
                             'replace').split('<')[0].strip()
            comment = unicode(change.description(), "utf-8", 'replace')
            for repo_file in change.files():
                if repo_file.startswith(self.repo_prefix):
                    title = self._file_to_title(repo_file)
                    try:
                        rev = change[repo_file].filerev()
                    except mercurial.revlog.LookupError:
                        rev = -1
                    yield title, rev, date, author, comment

    def all_pages(self):
        """Iterate over the titles of all pages in the wiki."""

        for filename in os.listdir(self.path):
            file_path = os.path.join(self.path, filename)
            if (os.path.isfile(file_path)
                and not os.path.islink(file_path)
                and not filename.startswith('.')):
                yield werkzeug.url_unquote(filename)

    def changed_since(self, rev):
        """Return all pages that changed since specified repository revision."""

        try:
            last = self.repo.lookup(int(rev))
        except IndexError:
            for page in self.all_pages():
                yield page
            return
        current = self.repo.lookup('tip')
        status = self.repo.status(current, last)
        modified, added, removed, deleted, unknown, ignored, clean = status
        for filename in modified+added+removed+deleted:
            if filename.startswith(self.repo_prefix):
                yield self._file_to_title(filename)


class WikiSubdirectoryStorage(WikiStorage):
    """
    A version of WikiStorage that keeps the subpages in real subdirectories in
    the filesystem.

    """

    periods_re = re.compile(r'^[.]|(?<=/)[.]')
    slashes_re = re.compile(r'^[/]|(?<=/)[/]')

    def _title_to_file(self, title):
        """Modified escaping allowing (some) slashes and spaces."""

        title = unicode(title).strip()
        escaped = werkzeug.url_quote(title, safe='/ ')
        escaped = self.periods_re.sub('%2E', escaped)
        escaped = self.slashes_re.sub('%2F', escaped)
        path = os.path.join(self.repo_prefix, escaped)
        return path

    def save_file(self, title, file_name, author=u'', comment=u'', parent=None):
        """
        Save the file and make the subdirectories if needed.
        """

        file_path = self._file_path(title)
        self._check_path(file_path)
        dir_path = os.path.dirname(file_path)
        try:
            os.makedirs(dir_path)
        except OSError, e:
            if e.errno == 17 and not os.path.isdir(dir_path):
                raise ForbiddenErr(
                    _(u"Can't make subpages of existing pages"))
            elif e.errno != 17:
                raise
        super(WikiSubdirectoryStorage, self).save_file(title, file_name,
                                                       author, comment, parent)

    def delete_page(self, title, author=u'', comment=u''):
        """
        Remove empty directories after deleting a page.

        Note that Mercurial doesn't track directories, so we don't have to
        commit after removing empty directories.
        """

        super(WikiSubdirectoryStorage, self).delete_page(title, author, comment)
        file_path = self._file_path(title)
        self._check_path(file_path)
        dir_path = os.path.dirname(file_path)
        os.removedirs(dir_path)

    def all_pages(self):
        """Iterate over the titles of all pages in the wiki. Include subdirectories."""

        for (dirpath, dirnames, filenames) in os.walk(self.path):
            path = dirpath[len(self.path)+1:]
            for name in filenames:
                filename = os.path.join(path, name)
                if (os.path.isfile(os.path.join(self.path, filename))
                    and not filename.startswith('.')):
                    yield werkzeug.url_unquote(filename)


class WikiParser(object):
    r"""
    Responsible for generating HTML markup from the wiki markup.

    The parser works on two levels. On the block level, it analyzes lines
    of text and decides what kind of block element they belong to (block
    elements include paragraphs, lists, headings, preformatted blocks).
    Lines belonging to the same block are joined together, and a second
    pass is made using regular expressions to parse line-level elements,
    such as links, bold and italic text and smileys.

    Some block-level elements, such as preformatted blocks, consume additional
    lines from the input until they encounter the end-of-block marker, using
    lines_until. Most block-level elements are just runs of marked up lines
    though.


    """

    bullets_pat = ur"^\s*[*]+\s+"
    heading_pat = ur"^\s*=+"
    quote_pat = ur"^[>]+\s+"
    block = {
        # "name": (priority, ur"pattern"),
        "bullets": (10, bullets_pat),
        "code": (20, ur"^[{][{][{]+\s*$"),
        "conflict": (30, ur"^<<<<<<< local\s*$"),
        "empty": (40, ur"^\s*$"),
        "heading": (50, heading_pat),
        "indent": (60, ur"^[ \t]+"),
        "macro":(70, ur"^<<\w+\s*$"),
        "quote": (80, quote_pat),
        "rule": (90, ur"^\s*---+\s*$"),
        "syntax": (100, ur"^\{\{\{\#![\w+#.-]+\s*$"),
        "table": (110, ur"^\|"),
    }
    image_pat = (ur"\{\{(?P<image_target>([^|}]|}[^|}])*)"
                 ur"(\|(?P<image_text>([^}]|}[^}])*))?}}")
    smilies = {
        r':)': "smile.png",
        r':(': "frown.png",
        r':P': "tongue.png",
        r':D': "grin.png",
        r';)': "wink.png",
    }
    punct = {
        r'...': "&hellip;",
        r'--': "&ndash;",
        r'---': "&mdash;",
        r'~': "&nbsp;",
        r'\~': "~",
        r'~~': "&sim;",
        r'(C)': "&copy;",
        r'-->': "&rarr;",
        r'<--': "&larr;",
        r'(R)': "&reg;",
        r'(TM)': "&trade;",
        r'%%': "&permil;",
        r'``': "&ldquo;",
        r"''": "&rdquo;",
        r",,": "&bdquo;",
    }
    markup = {
        # "name": (priority, ur"pattern"),
        "bold": (10, ur"[*][*]"),
        "code": (20, ur"[{][{][{](?P<code_text>([^}]|[^}][}]|[^}][}][}])"
                ur"*[}]*)[}][}][}]"),
        "free_link": (30, ur"""(http|https|ftp)://\S+[^\s.,:;!?()'"=+<>-]"""),
        "italic": (40 , ur"//"),
        "link": (50, ur"\[\[(?P<link_target>([^|\]]|\][^|\]])+)"
                ur"(\|(?P<link_text>([^\]]|\][^\]])+))?\]\]"),
        "image": (60, image_pat),
        "linebreak": (70, ur"\\\\"),
        "macro": (80, ur"[<][<](?P<macro_name>\w+)\s+"
                 ur"(?P<macro_text>([^>]|[^>][>])+)[>][>]"),
        "mail": (90, ur"""(mailto:)?\S+@\S+(\.[^\s.,:;!?()'"/=+<>-]+)+"""),
        "math": (100, ur"\$\$(?P<math_text>[^$]+)\$\$"),
        "mono": (110, ur"##"),
        "newline": (120, ur"\n"),
        "punct": (130, ur'(^|\b|(?<=\s))(%s)((?=[\s.,:;!?)/&=+"\'—-])|\b|$)' %
                  ur"|".join(re.escape(k) for k in punct)),
        "table": (140, ur"=?\|=?"),
        "text": (150, ur".+?"),
    }


    def __init__(self, lines, wiki_link, wiki_image,
                 wiki_syntax=None, wiki_math=None, smilies=None):
        self.wiki_link = wiki_link
        self.wiki_image = wiki_image
        self.wiki_syntax = wiki_syntax
        self.wiki_math = wiki_math
        self.enumerated_lines = enumerate(lines)
        if smilies is not None:
            self.smilies = smilies
        self.compile_patterns()
        self.headings = {}
        self.stack = []
        self.line_no = 0

    def compile_patterns(self):
        self.quote_re = re.compile(self.quote_pat, re.U)
        self.heading_re = re.compile(self.heading_pat, re.U)
        self.bullets_re = re.compile(self.bullets_pat, re.U)
        patterns = ((k, p) for (k, (x, p)) in
                    sorted(self.block.iteritems(), key=lambda x: x[1][0]))
        self.block_re = re.compile(ur"|".join("(?P<%s>%s)" % pat
                                   for pat in patterns), re.U)
        self.code_close_re = re.compile(ur"^\}\}\}\s*$", re.U)
        self.macro_close_re = re.compile(ur"^>>\s*$", re.U)
        self.conflict_close_re = re.compile(ur"^>>>>>>> other\s*$", re.U)
        self.conflict_sep_re = re.compile(ur"^=======\s*$", re.U)
        self.image_re = re.compile(self.image_pat, re.U)
        smileys = ur"|".join(re.escape(k) for k in self.smilies)
        smiley_pat = (ur"(^|\b|(?<=\s))(?P<smiley_face>%s)"
                      ur"((?=[\s.,:;!?)/&=+-])|$)" % smileys)
        self.markup['smiley'] = (125, smiley_pat)
        patterns = ((k, p) for (k, (x, p)) in
                    sorted(self.markup.iteritems(), key=lambda x: x[1][0]))
        self.markup_re = re.compile(ur"|".join("(?P<%s>%s)" % pat
                                    for pat in patterns), re.U)

    def __iter__(self):
        return self.parse()

    @classmethod
    def extract_links(cls, text):
        links = []
        def link(addr, label=None, class_=None, image=None, alt=None, lineno=0):
            addr = addr.strip()
            if external_link(addr):
                return u''
            if '#' in addr:
                addr, chunk = addr.split('#', 1)
            if addr == u'':
                return u''
            links.append((addr, label))
            return u''
        lines = text.split('\n')
        for part in cls(lines, link, link):
            for ret in links:
                yield ret
            links[:] = []

    def parse(self):
        """Parse a list of lines of wiki markup, yielding HTML for it."""

        self.headings = {}
        self.stack = []
        self.line_no = 0

        def key(enumerated_line):
            line_no, line = enumerated_line
            match = self.block_re.match(line)
            if match:
                return match.lastgroup
            return "paragraph"

        for kind, block in itertools.groupby(self.enumerated_lines, key):
            func = getattr(self, "_block_%s" % kind)
            for part in func(block):
                yield part

    def parse_line(self, line):
        """
        Find all the line-level markup and return HTML for it.

        """

        for match in self.markup_re.finditer(line):
            func = getattr(self, "_line_%s" % match.lastgroup)
            yield func(match.groupdict())

    def pop_to(self, stop):
        """
            Pop from the stack until the specified tag is encoutered.
            Return string containing closing tags of everything popped.
        """
        tags = []
        tag = None
        try:
            while tag != stop:
                tag = self.stack.pop()
                tags.append(tag)
        except IndexError:
            pass
        return u"".join(u"</%s>" % tag for tag in tags)

    def lines_until(self, close_re):
        """Get lines from input until the closing markup is encountered."""

        self.line_no, line = self.enumerated_lines.next()
        while not close_re.match(line):
            yield line.rstrip()
            line_no, line = self.enumerated_lines.next()

# methods for the markup inside lines:

    def _line_table(self, groups):
        return groups["table"]

    def _line_linebreak(self, groups):
        return u'<br>'

    def _line_smiley(self, groups):
        smiley = groups["smiley_face"]
        try:
            url = self.smilies[smiley]
        except KeyError:
            url = ''
        return self.wiki_image(url, smiley, class_="smiley")

    def _line_bold(self, groups):
        if 'b' in self.stack:
            return self.pop_to('b')
        else:
            self.stack.append('b')
            return u"<b>"

    def _line_italic(self, groups):
        if 'i' in self.stack:
            return self.pop_to('i')
        else:
            self.stack.append('i')
            return u"<i>"

    def _line_mono(self, groups):
        if 'tt' in self.stack:
            return self.pop_to('tt')
        else:
            self.stack.append('tt')
            return u"<tt>"

    def _line_punct(self, groups):
        text = groups["punct"]
        return self.punct.get(text, text)

    def _line_newline(self, groups):
        return "\n"

    def _line_text(self, groups):
        return werkzeug.escape(groups["text"])

    def _line_math(self, groups):
        if self.wiki_math:
            return self.wiki_math(groups["math_text"])
        else:
            return "<var>%s</var>" % werkzeug.escape(groups["math_text"])

    def _line_code(self, groups):
        return u'<code>%s</code>' % werkzeug.escape(groups["code_text"])

    def _line_free_link(self, groups):
        groups['link_target'] = groups['free_link']
        return self._line_link(groups)

    def _line_mail(self, groups):
        addr = groups['mail']
        groups['link_text'] = addr
        if not addr.startswith(u'mailto:'):
            addr = u'mailto:%s' % addr
        groups['link_target'] = addr
        return self._line_link(groups)

    def _line_link(self, groups):
        target = groups['link_target']
        text = groups.get('link_text')
        if not text:
            text = target
            if '#' in text:
                text, chunk = text.split('#', 1)
        match = self.image_re.match(text)
        if match:
            image = self._line_image(match.groupdict())
            return self.wiki_link(target, text, image=image)
        return self.wiki_link(target, text)

    def _line_image(self, groups):
        target = groups['image_target']
        alt = groups.get('image_text')
        if alt is None:
            alt = target
        return self.wiki_image(target, alt)

    def _line_macro(self, groups):
        name = groups['macro_name']
        text = groups['macro_text'].strip()
        return u'<span class="%s">%s</span>' % (
            werkzeug.escape(name, quote=True),
            werkzeug.escape(text))

# methods for the block (multiline) markup:

    def _block_code(self, block):
        for self.line_no, part in block:
            inside = u"\n".join(self.lines_until(self.code_close_re))
            yield werkzeug.html.pre(werkzeug.html(inside), class_="code",
                                    id="line_%d" % self.line_no)

    def _block_syntax(self, block):
        for self.line_no, part in block:
            syntax = part.lstrip('{#!').strip()
            inside = u"\n".join(self.lines_until(self.code_close_re))
            if self.wiki_syntax:
                return self.wiki_syntax(inside, syntax=syntax,
                                        line_no=self.line_no)
            else:
                return [werkzeug.html.div(werkzeug.html.pre(
                    werkzeug.html(inside), id="line_%d" % self.line_no),
                    class_="highlight")]

    def _block_macro(self, block):
        for self.line_no, part in block:
            name = part.lstrip('<').strip()
            inside = u"\n".join(self.lines_until(self.macro_close_re))
            yield u'<div class="%s">%s</div>' % (
                werkzeug.escape(name, quote=True),
                werkzeug.escape(inside))

    def _block_paragraph(self, block):
        parts = []
        first_line = None
        for self.line_no, part in block:
            if first_line is None:
                first_line = self.line_no
            parts.append(part)
        text = u"".join(self.parse_line(u"".join(parts)))
        yield werkzeug.html.p(text, self.pop_to(""), id="line_%d" % first_line)

    def _block_indent(self, block):
        parts = []
        first_line = None
        for self.line_no, part in block:
            if first_line is None:
                first_line = self.line_no
            parts.append(part.rstrip())
        text = u"\n".join(parts)
        yield werkzeug.html.pre(werkzeug.html(text), id="line_%d" % first_line)

    def _block_table(self, block):
        first_line = None
        in_head = False
        for self.line_no, line in block:
            if first_line is None:
                first_line = self.line_no
                yield u'<table id="line_%d">' % first_line
            table_row = line.strip()
            is_header = table_row.startswith('|=') and table_row.endswith('=|')
            if not in_head and is_header:
                in_head = True
                yield '<thead>'
            elif in_head and not is_header:
                in_head = False
                yield '</thead>'
            yield '<tr>'
            in_cell = False
            in_th = False

            for part in self.parse_line(table_row):
                if part in ('=|', '|', '=|=', '|='):
                    if in_cell:
                        if in_th:
                            yield '</th>'
                        else:
                            yield '</td>'
                        in_cell = False
                    if part in ('=|=', '|='):
                        in_th = True
                    else:
                        in_th = False
                else:
                    if not in_cell:
                        if in_th:
                            yield '<th>'
                        else:
                            yield '<td>'
                        in_cell = True
                    yield part
            if in_cell:
                if in_th:
                    yield '</th>'
                else:
                    yield '</td>'
            yield '</tr>'
        yield u'</table>'

    def _block_empty(self, block):
        yield u''

    def _block_rule(self, block):
        for self.line_no, line in block:
            yield werkzeug.html.hr()

    def _block_heading(self, block):
        for self.line_no, line in block:
            level = min(len(self.heading_re.match(line).group(0).strip()), 5)
            self.headings[level-1] = self.headings.get(level-1, 0)+1
            label = u"-".join(str(self.headings.get(i, 0))
                              for i in range(level))
            yield werkzeug.html.a(name="head-%s" % label)
            yield u'<h%d id="line_%d">%s</h%d>' % (level, self.line_no,
                werkzeug.escape(line.strip("= \t\n\r\v")), level)

    def _block_bullets(self, block):
        level = 0
        in_ul = False
        for self.line_no, line in block:
            nest = len(self.bullets_re.match(line).group(0).strip())
            while nest > level:
                if in_ul:
                    yield '<li>'
                yield '<ul id="line_%d">' % self.line_no
                in_ul = True
                level += 1
            while nest < level:
                yield '</li></ul>'
                in_ul = False
                level -= 1
            if nest == level and not in_ul:
                yield '</li>'
            content = line.lstrip().lstrip('*').strip()
            yield '<li>%s%s' % (u"".join(self.parse_line(content)),
                                self.pop_to(""))
            in_ul = False
        yield '</li></ul>'*level

    def _block_quote(self, block):
        level = 0
        in_p = False
        for self.line_no, line in block:
            nest = len(self.quote_re.match(line).group(0).strip())
            if nest == level:
                yield u'\n'
            while nest > level:
                if in_p:
                    yield '%s</p>' % self.pop_to("")
                    in_p = False
                yield '<blockquote>'
                level += 1
            while nest < level:
                if in_p:
                    yield '%s</p>' % self.pop_to("")
                    in_p = False
                yield '</blockquote>'
                level -= 1
            content = line.lstrip().lstrip('>').strip()
            if not in_p:
                yield '<p id="line_%d">' % self.line_no
                in_p = True
            yield u"".join(self.parse_line(content))
        if in_p:
            yield '%s</p>' % self.pop_to("")
        yield '</blockquote>'*level

    def _block_conflict(self, block):
        for self.line_no, part in block:
            yield u'<div class="conflict">'
            local = u"\n".join(self.lines_until(self.conflict_sep_re))
            yield werkzeug.html.pre(werkzeug.html(local),
                                    class_="local",
                                    id="line_%d" % self.line_no)
            other = u"\n".join(self.lines_until(self.conflict_close_re))
            yield werkzeug.html.pre(werkzeug.html(other),
                                    class_="other",
                                    id="line_%d" % self.line_no)
            yield u'</div>'


class WikiWikiParser(WikiParser):
    """A version of WikiParser that recognizes WikiWord links."""

    markup = dict(WikiParser.markup)
    camel_link = ur"\w+[%s]\w+" % re.escape(
        u''.join(unichr(i) for i in xrange(sys.maxunicode)
        if unicodedata.category(unichr(i))=='Lu'))
    markup["camel_link"] = (105, camel_link)
    markup["camel_nolink"] = (106, ur"[!~](?P<camel_text>%s)" % camel_link)

    def _line_camel_link(self, groups):
        groups['link_target'] = groups['camel_link']
        return self._line_link(groups)

    def _line_camel_nolink(self, groups):
        return werkzeug.escape(groups["camel_text"])


class WikiSearch(object):
    """
    Responsible for indexing words and links, for fast searching and
    backlinks. Uses a cache directory to store the index files.
    """

    word_pattern = re.compile(ur"""\w[-~&\w]+\w""", re.UNICODE)
    jword_pattern = re.compile(
ur"""[ｦ-ﾟ]+|[ぁ-ん～ー]+|[ァ-ヶ～ー]+|[0-9A-Za-z]+|"""
ur"""[０-９Ａ-Ｚａ-ｚΑ-Ωα-ωА-я]+|"""
ur"""[^- !"#$%&'()*+,./:;<=>?@\[\\\]^_`{|}"""
ur"""‾｡｢｣､･　、。，．・：；？！゛゜´｀¨"""
ur"""＾￣＿／〜‖｜…‥‘’“”"""
ur"""（）〔〕［］｛｝〈〉《》「」『』【】＋−±×÷"""
ur"""＝≠＜＞≦≧∞∴♂♀°′″℃￥＄¢£"""
ur"""％＃＆＊＠§☆★○●◎◇◆□■△▲▽▼※〒"""
ur"""→←↑↓〓∈∋⊆⊇⊂⊃∪∩∧∨¬⇒⇔∠∃∠⊥"""
ur"""⌒∂∇≡≒≪≫√∽∝∵∫∬Å‰♯♭♪†‡¶◾"""
ur"""─│┌┐┘└├┬┤┴┼"""
ur"""━┃┏┓┛┗┣┫┻╋"""
ur"""┠┯┨┷┿┝┰┥┸╂"""
ur"""ｦ-ﾟぁ-ん～ーァ-ヶ"""
ur"""0-9A-Za-z０-９Ａ-Ｚａ-ｚΑ-Ωα-ωА-я]+""", re.UNICODE)
    _con = {}

    def __init__(self, cache_path, lang, storage):
        self.path = cache_path
        self.storage = storage
        self.lang = lang
        if lang == "ja":
            self.split_text = self.split_japanese_text
        self.filename = os.path.join(cache_path, 'index.sqlite3')
        if not os.path.isdir(self.path):
            self.empty = True
            os.makedirs(self.path)
        elif not os.path.exists(self.filename):
            self.empty = True
        else:
            self.empty = False
        con = self.con # sqlite3.connect(self.filename)
        self.con.execute('CREATE TABLE IF NOT EXISTS titles '
                '(id INTEGER PRIMARY KEY, title VARCHAR);')
        self.con.execute('CREATE TABLE IF NOT EXISTS words '
                '(word VARCHAR, page INTEGER, count INTEGER);')
        self.con.execute('CREATE INDEX IF NOT EXISTS index1 '
                         'ON words (page);')
        self.con.execute('CREATE INDEX IF NOT EXISTS index2 '
                         'ON words (word);')
        self.con.execute('CREATE TABLE IF NOT EXISTS links '
                '(src INTEGER, target INTEGER, label VARCHAR, number INTEGER);')
        self.con.commit()
        self.stop_words_re = re.compile(u'^('+u'|'.join(re.escape(_(
u"""am ii iii per po re a about above
across after afterwards again against all almost alone along already also
although always am among ain amongst amoungst amount an and another any aren
anyhow anyone anything anyway anywhere are around as at back be became because
become becomes becoming been before beforehand behind being below beside
besides between beyond bill both but by can cannot cant con could couldnt
describe detail do done down due during each eg eight either eleven else etc
elsewhere empty enough even ever every everyone everything everywhere except
few fifteen fifty fill find fire first five for former formerly forty found
four from front full further get give go had has hasnt have he hence her here
hereafter hereby herein hereupon hers herself him himself his how however
hundred i ie if in inc indeed interest into is it its itself keep last latter
latterly least isn less made many may me meanwhile might mill mine more
moreover most mostly move much must my myself name namely neither never
nevertheless next nine no nobody none noone nor not nothing now nowhere of off
often on once one only onto or other others otherwise our ours ourselves out
over own per perhaps please pre put rather re same see seem seemed seeming
seems serious several she should show side since sincere six sixty so some
somehow someone something sometime sometimes somewhere still such take ten than
that the their theirs them themselves then thence there thereafter thereby
therefore therein thereupon these they thick thin third this those though three
through throughout thru thus to together too toward towards twelve twenty two
un under ve until up upon us very via was wasn we well were what whatever when
whence whenever where whereafter whereas whereby wherein whereupon wherever
whether which while whither who whoever whole whom whose why will with within
without would yet you your yours yourself yourselves""")).split())
+ur')$|.*\d.*', re.U|re.I|re.X)



    @property
    def con(self):
        """Keep one connection per thread."""

        thread_id = thread.get_ident()
        try:
            return self._con[thread_id]
        except KeyError:
            connection = sqlite3.connect(self.filename)
            connection.isolation_level = None
            self._con[thread_id] = connection
            return connection

    def split_text(self, text, stop=True):
        """Splits text into words, removing stop words"""

        for match in self.word_pattern.finditer(text):
            word = match.group(0)
            if not (stop and self.stop_words_re.match(word)):
                yield word.lower()

    def split_japanese_text(self, text, stop=True):
        """Splits text into words, including rules for Japanese"""

        for match in self.word_pattern.finditer(text):
            word = match.group(0)
            got_japanese = False
            for m in self.jword_pattern.finditer(word):
                w = m.group(0)
                got_japanese = True
                if not (stop and self.stop_words_re.match(w)):
                    yield w.lower()
            if not (got_japanese or stop and self.stop_words_re.match(word)):
                yield word.lower()

    def count_words(self, words):
        count = {}
        for word in words:
            count[word] = count.get(word, 0)+1
        return count

    def title_id(self, title, con):
        c = con.execute('SELECT id FROM titles WHERE title=?;', (title,))
        idents = c.fetchone()
        if idents is None:
            con.execute('INSERT INTO titles (title) VALUES (?);', (title,))
            c = con.execute('SELECT LAST_INSERT_ROWID();')
            idents = c.fetchone()
        return idents[0]

    def update_words(self, title, text, cursor):
        title_id = self.title_id(title, cursor)
        words = self.count_words(self.split_text(text))
        title_words = self.count_words(self.split_text(title))
        for word, count in title_words.iteritems():
            words[word] = words.get(word, 0) + count
        cursor.execute('DELETE FROM words WHERE page=?;', (title_id,))
        for word, count in words.iteritems():
            cursor.execute('INSERT INTO words VALUES (?, ?, ?);',
                             (word, title_id, count))

    def update_links(self, title, links_and_labels, cursor):
        title_id = self.title_id(title, cursor)
        cursor.execute('DELETE FROM links WHERE src=?;', (title_id,))
        for number, (link, label) in enumerate(links_and_labels):
            cursor.execute('INSERT INTO links VALUES (?, ?, ?, ?);',
                             (title_id, link, label, number))

    def orphaned_pages(self):
        """Gives all pages with no links to them."""

        con = self.con
        try:
            sql = ('SELECT title FROM titles '
                   'WHERE NOT EXISTS '
                   '(SELECT * FROM links WHERE target=title) '
                   'ORDER BY title;')
            for (title,) in con.execute(sql):
                yield unicode(title)
        finally:
            con.commit()

    def wanted_pages(self):
        """Gives all pages that are linked to, but don't exist, together with
        the number of links."""

        con = self.con
        try:
            sql = ('SELECT COUNT(*), target FROM links '
                   'WHERE NOT EXISTS '
                   '(SELECT * FROM titles WHERE target=title) '
                   'GROUP BY target ORDER BY -COUNT(*);')
            for (refs, db_title,) in con.execute(sql):
                title = unicode(db_title)
                if not external_link(title) and not title.startswith('+'):
                    yield refs, title
        finally:
            con.commit()


    def page_backlinks(self, title):
        """Gives a list of pages linking to specified page."""

        con = self.con # sqlite3.connect(self.filename)
        try:
            sql = ('SELECT DISTINCT(titles.title) '
                   'FROM links, titles '
                   'WHERE links.target=? AND titles.id=links.src '
                   'ORDER BY titles.title;')
            for (backlink,) in con.execute(sql, (title,)):
                yield unicode(backlink)
        finally:
            con.commit()

    def page_links(self, title):
        """Gives a list of links on specified page."""

        con = self.con # sqlite3.connect(self.filename)
        try:
            title_id = self.title_id(title, con)
            sql = 'SELECT target FROM links WHERE src=? ORDER BY number;'
            for (link,) in con.execute(sql, (title_id,)):
                yield unicode(link)
        finally:
            con.commit()

    def page_links_and_labels (self, title):
        con = self.con # sqlite3.connect(self.filename)
        try:
            title_id = self.title_id(title, con)
            sql = 'SELECT target, label FROM links WHERE src=? ORDER BY number;'
            for link, label in con.execute(sql, (title_id,)):
                yield unicode(link), unicode(label)
        finally:
            con.commit()

    def find(self, words):
        """Iterator of all pages containing the words, and their scores."""

        con = self.con
        try:
            ranks = []
            for word in words:
                # Calculate popularity of each word.
                sql = 'SELECT SUM(words.count) FROM words WHERE word LIKE ?;'
                rank = con.execute(sql, ('%%%s%%' % word,)).fetchone()[0]
                # If any rank is 0, there will be no results anyways
                if not rank:
                    return
                ranks.append((rank, word))
            ranks.sort()
            # Start with the least popular word. Get all pages that contain it.
            first_rank, first = ranks[0]
            rest = ranks[1:]
            sql = ('SELECT words.page, titles.title, SUM(words.count) '
                   'FROM words, titles '
                   'WHERE word LIKE ? AND titles.id=words.page '
                   'GROUP BY words.page;')
            first_counts = con.execute(sql, ('%%%s%%' % first,))
            # Check for the rest of words
            for title_id, title, first_count in first_counts:
                # Score for the first word
                score = float(first_count)/first_rank
                for rank, word in rest:
                    sql = ('SELECT SUM(count) FROM words '
                           'WHERE page=? AND word LIKE ?;')
                    count = con.execute(sql,
                        (title_id, '%%%s%%' % word)).fetchone()[0]
                    if not count:
                        # If page misses any of the words, its score is 0
                        score = 0
                        break
                    score += float(count)/rank
                if score > 0:
                    yield int(100*score), unicode(title)
        finally:
            con.commit()

    def reindex_page(self, page, title, cursor, text=None):
        """Updates the content of the database, needs locks around."""

        if text is None:
            get_text = getattr(page, 'plain_text', lambda: u'')
            try:
                text = get_text()
            except NotFoundErr:
                text = u''
        extract_links = getattr(page, 'extract_links', lambda x: [])
        if text:
            self.update_links(title, extract_links(text), cursor=cursor)
        self.update_words(title, text, cursor=cursor)

    def update_page(self, page, title, data=None, text=None):
        """Updates the index with new page content, for a single page."""

        if text is None and data is not None:
            text = unicode(data, self.storage.charset, 'replace')
        cursor = self.con.cursor()
        cursor.execute('BEGIN IMMEDIATE TRANSACTION;')
        try:
            self.set_last_revision(self.storage.repo_revision())
            self.reindex_page(page, title, cursor, text)
            cursor.execute('COMMIT TRANSACTION;')
        except:
            cursor.execute('ROLLBACK;')
            raise

    def reindex(self, wiki, request,  pages):
        """Updates specified pages in bulk."""

        cursor = self.con.cursor()
        cursor.execute('BEGIN IMMEDIATE TRANSACTION;')
        try:
            for title in pages:
                page = wiki.get_page(request, title)
                self.reindex_page(page, title, cursor)
            cursor.execute('COMMIT TRANSACTION;')
            self.empty = False
        except:
            cursor.execute('ROLLBACK;')
            raise

    def set_last_revision(self, rev):
        """Store the last indexed repository revision."""

        # We use % here because the sqlite3's substitiution doesn't work
        # We store revision 0 as 1, 1 as 2, etc. because 0 means "no revision"
        self.con.execute('PRAGMA USER_VERSION=%d;' % (int(rev+1),))

    def get_last_revision(self):
        """Retrieve the last indexed repository revision."""

        con = self.con
        c = con.execute('PRAGMA USER_VERSION;')
        rev = c.fetchone()[0]
        # -1 means "no revision", 1 means revision 0, 2 means revision 1, etc.
        return rev-1

    def update(self, wiki, request):
        """Reindex al pages that changed since last indexing."""

        last_rev = self.get_last_revision()
        if last_rev == -1:
            changed = self.storage.all_pages()
        else:
            changed = self.storage.changed_since(last_rev)
        self.reindex(wiki, request, changed)
        rev = self.storage.repo_revision()
        self.set_last_revision(rev)

class WikiResponse(werkzeug.BaseResponse, werkzeug.ETagResponseMixin,
                   werkzeug.CommonResponseDescriptorsMixin):
    """A typical HTTP response class made out of Werkzeug's mixins."""

    def make_conditional(self, request):
        ret = super(WikiResponse, self).make_conditional(request)
        # Remove all headers if it's 304, according to
        # http://www.w3.org/Protocols/rfc2616/rfc2616-sec10.html#sec10.3.5
        if self.status.startswith('304'):
            self.response = []
            try:
                del self.content_type
            except AttributeError:
                pass
            try:
                del self.content_length
            except AttributeError:
                pass
            try:
                del self.headers['Content-length']
            except (KeyError, IndexError):
                pass
            try:
                del self.headers['Content-type']
            except (KeyError, IndexError):
                pass
        return ret

class WikiTempFile(object):
    """Wrap a file for uploading content."""

    def __init__(self, tmppath):
        self.tmppath = tempfile.mkdtemp(dir=tmppath)
        self.tmpname = os.path.join(self.tmppath, 'saved')
        self.f = open(self.tmpname, "wb")

    def read(self, *args, **kw):
        return self.f.read(*args, **kw)

    def readlines(self, *args, **kw):
        return self.f.readlines(*args, **kw)

    def write(self, *args, **kw):
        return self.f.write(*args, **kw)

    def seek(self, *args, **kw):
        return self.f.seek(*args, **kw)

    def truncate(self, *args, **kw):
        return self.f.truncate(*args, **kw)

    def close(self, *args, **kw):
        ret = self.f.close(*args, **kw)
        try:
            os.unlink(self.tmpname)
        except OSError:
            pass
        try:
            os.rmdir(self.tmppath)
        except OSError:
            pass
        return ret


class WikiRequest(werkzeug.BaseRequest, werkzeug.ETagRequestMixin):
    """
    A Werkzeug's request with additional functions for handling file
    uploads and wiki-specific link generation.
    """

    charset = 'utf-8'
    encoding_errors = 'ignore'

    def __init__(self, wiki, adapter, environ, **kw):
        werkzeug.BaseRequest.__init__(self, environ, shallow=False, **kw)
        self.wiki = wiki
        self.adapter = adapter
        self.tmpfiles = []
        self.tmppath = wiki.path
        # Whether to print the css for highlighting
        self.print_highlight_styles = True

    def get_url(self, title=None, view=None, method='GET',
                external=False, **kw):
        if view is None:
            view = self.wiki.view
        if title is not None:
            kw['title'] = title.strip()
        return self.adapter.build(view, kw, method=method,
                                  force_external=external)

    def get_download_url(self, title):
        return self.get_url(title, view=self.wiki.download)

    def get_author(self):
        """Try to guess the author name. Use IP address as last resort."""

        try:
            cookie = werkzeug.url_unquote(self.cookies.get("author", ""))
        except UnicodeError:
            cookie = None
        try:
            auth = werkzeug.url_unquote(self.environ.get('REMOTE_USER', ""))
        except UnicodeError:
            auth = None
        author = (self.form.get("author") or cookie or auth or self.remote_addr)
        return author

    def _get_file_stream(self, total_content_length=None, content_type=None,
                         filename=None, content_length=None):
        """Save all the POSTs to temporary files."""

        temp_file = WikiTempFile(self.tmppath)
        self.tmpfiles.append(temp_file)
        return temp_file

    def cleanup(self):
        """Clean up the temporary files created by POSTs."""

        for temp_file in self.tmpfiles:
            temp_file.close()
        self.tmpfiles = []

class WikiPage(object):
    """Everything needed for rendering a page."""

    def __init__(self, wiki, request, title, mime):
        self.request = request
        self.title = title
        self.mime = mime
        # for now we just use the globals from wiki object
        self.get_url = self.request.get_url
        self.get_download_url = self.request.get_download_url
        self.wiki = wiki
        self.storage = self.wiki.storage
        self.index = self.wiki.index
        self.config = self.wiki.config

    def date_html(self, datetime):
        """
        Create HTML for a date, according to recommendation at
        http://microformats.org/wiki/date
        """

        text = datetime.strftime('%Y-%m-%d %H:%M')
        # We are going for YYYY-MM-DDTHH:MM:SSZ
        title = datetime.strftime('%Y-%m-%dT%H:%M:%SZ')
        html = werkzeug.html.abbr(text, class_="date", title=title)
        return html


    def wiki_link(self, addr, label=None, class_=None, image=None, lineno=0):
        """Create HTML for a wiki link."""

        addr = addr.strip()
        text = werkzeug.escape(label or addr)
        chunk = ''
        if class_ is not None:
            classes = [class_]
        else:
            classes = []
        if external_link(addr):
            if addr.startswith('mailto:'):
                class_ = 'external email'
                text = text.replace('@', '&#64;').replace('.', '&#46;')
                href = addr.replace('@', '%40').replace('.', '%2E')
            else:
                classes.append('external')
                href = werkzeug.escape(addr, quote=True)
        else:
            if '#' in addr:
                addr, chunk = addr.split('#', 1)
                chunk = '#'+chunk
            if addr.startswith('+'):
                href = '/'.join([self.request.script_root,
                                 '+'+werkzeug.escape(addr[1:], quote=True)])
                classes.append('special')
            elif addr == u'':
                href = chunk
                classes.append('anchor')
            else:
                classes.append('wiki')
                href = self.get_url(addr) + chunk
                if addr not in self.storage:
                    classes.append('nonexistent')
        class_ = ' '.join(classes) or None
        return werkzeug.html.a(image or text, href=href, class_=class_,
                               title=addr+chunk)

    def wiki_image(self, addr, alt, class_='wiki', lineno=0):
        """Create HTML for a wiki image."""

        addr = addr.strip()
        html = werkzeug.html
        chunk = ''
        if external_link(addr):
            return html.img(src=werkzeug.url_fix(addr), class_="external",
                            alt=alt)
        if '#' in addr:
            addr, chunk = addr.split('#', 1)
        if addr == '':
            return html.a(name=chunk)
        if addr in self.storage:
            mime = page_mime(addr)
            if mime.startswith('image/'):
                return html.img(src=self.get_download_url(addr), class_=class_,
                                alt=alt)
            else:
                return html.img(href=self.get_download_url(addr), alt=alt)
        else:
            return html.a(html(alt), href=self.get_url(addr))

    def search_form(self):
        html = werkzeug.html
        return html.form(html.div(html.input(name="q", class_="search"),
                html.input(class_="button", type_="submit", value=_(u'Search')),
            ), method="GET", class_="search",
            action=self.get_url(None, self.wiki.search))

    def logo(self):
        html = werkzeug.html
        img = html.img(alt=u"[%s]" % self.wiki.front_page,
                       src=self.get_download_url(self.wiki.logo_page))
        return html.a(img, class_='logo', href=self.get_url(self.wiki.front_page))

    def menu(self):
        """Generate the menu items"""

        html = werkzeug.html
        if self.wiki.menu_page in self.storage:
            items = self.index.page_links_and_labels(self.wiki.menu_page)
        else:
            items = [
                (self.wiki.front_page, self.wiki.front_page),
                ('+history', _(u'Recent changes')),
            ]
        for link, label in items:
            if link == self.title:
                class_="current"
            else:
                class_ = None
            yield self.wiki_link(link, label, class_=class_)

    def header(self, special_title):
        html = werkzeug.html
        if self.wiki.logo_page in self.storage:
            yield self.logo()
        yield self.search_form()
        yield html.div(u" ".join(self.menu()), class_="menu")
        yield html.h1(html(special_title or self.title))

    def html_header(self, special_title, edit_url):
        e = lambda x: werkzeug.escape(x, quote=True)
        h = werkzeug.html
        yield h.title(u'%s - %s' % (e(special_title or self.title),
                                    e(self.wiki.site_name)))
        yield h.link(rel="stylesheet", type_="text/css",
                     href=self.get_url(None, self.wiki.pygments_css))
        yield h.link(rel="stylesheet", type_="text/css",
                     href=self.get_url(None, self.wiki.style_css))
        if special_title:
            yield h.meta(name="robots", content="NOINDEX,NOFOLLOW")
        if edit_url:
            yield h.link(rel="alternate", type_="application/wiki",
                         href=edit_url)
        yield h.link(rel="shortcut icon", type_="image/x-icon",
                     href=self.get_url(None, self.wiki.favicon_ico))
        yield h.link(rel="alternate", type_="application/rss+xml",
                     title=e("%s (RSS)" % self.wiki.site_name),
                     href=self.get_url(None, self.wiki.rss))
        yield h.link(rel="alternate", type_="application/rss+xml",
                     title=e("%s (ATOM)" % self.wiki.site_name),
                     href=self.get_url(None, self.wiki.atom))
        yield h.script(type_="text/javascript",
                     src=self.get_url(None, self.wiki.scripts_js))

    def footer(self, special_title, edit_url):
        if special_title:
            footer_links = [
                (_(u'Changes'), 'changes',
                 self.get_url(None, self.wiki.recent_changes)),
                (_(u'Index'), 'index',
                 self.get_url(None, self.wiki.all_pages)),
                (_(u'Orphaned'), 'orphaned',
                 self.get_url(None, self.wiki.orphaned)),
                (_(u'Wanted'), 'wanted',
                 self.get_url(None, self.wiki.wanted)),
            ]
        else:
            footer_links = [
                (_(u'Edit'), 'edit', edit_url),
                (_(u'History'), 'history',
                 self.get_url(self.title, self.wiki.history)),
                (_(u'Backlinks'), 'backlinks',
                 self.get_url(self.title, self.wiki.backlinks))
            ]
        for label, class_, url in footer_links:
            if url:
                yield werkzeug.html.a(werkzeug.html(label), href=url,
                                      class_=class_)
                yield u'\n'

    def render_content(self, content, special_title=None):
        """The main page template."""

        edit_url = None
        if not special_title:
            try:
                self.wiki._check_lock(self.title)
                edit_url = self.get_url(self.title, self.wiki.edit)
            except ForbiddenErr:
                pass

        yield u"""\
<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.01//EN"
"http://www.w3.org/TR/html4/strict.dtd">
<html><head>\n"""
        for part in self.html_header(special_title, edit_url):
            yield part
        yield u'\n</head><body><div class="header">\n'
        for part in self.header(special_title):
            yield part
        yield u'\n</div><div class="content">\n'
        for part in content:
            yield part
        if not special_title or not self.title:
            yield u'\n<div class="footer">\n'
            for part in self.footer(special_title, edit_url):
                yield part
            yield u'</div>'
        yield u'</div></body></html>'


    def pages_list(self, pages, message=None, link=None, _class=None):
        """Generate the content of a page list page."""

        yield werkzeug.html.p(werkzeug.escape(message) % {'link': link})
        yield u'<ul class="%s">' % werkzeug.escape(_class or 'pagelist')
        for title in pages:
            yield werkzeug.html.li(self.wiki_link(title))
        yield u'</ul>'

    def history_list(self):
        """Generate the content of the history page."""

        h = werkzeug.html
        max_rev = -1;
        title = self.title
        link = self.wiki_link(title)
        yield h.p(h(_(u'History of changes for %(link)s.')) % {'link': link})
        url = self.request.get_url(title, self.wiki.undo, method='POST')
        yield u'<form action="%s" method="POST"><ul class="history">' % url
        try:
            self.wiki._check_lock(title)
            read_only = False
        except ForbiddenErr:
            read_only = True
        for rev, date, author, comment in self.wiki.storage.page_history(title):
            if max_rev < rev:
                max_rev = rev
            if rev > 0:
                date_url = self.request.adapter.build(self.wiki.diff, {
                    'title': title, 'from_rev': rev-1, 'to_rev': rev})
            else:
                date_url = self.request.adapter.build(self.wiki.revision, {
                    'title': title, 'rev': rev})
            if read_only:
                button = u''
            else:
                button = h.input(type_="submit", name=str(rev),
                                 value=h(_(u'Undo')))
            yield h.li(h.a(self.date_html(date), href=date_url),
                       button, ' . . . . ', h.i(self.wiki_link(author)),
                       h.div(h(comment), class_="comment"))
        yield u'</ul>'
        yield h.input(type_="hidden", name="parent", value=max_rev)
        yield u'</form>'


    def dependencies(self):
        """Refresh the page when any of those pages was changed."""

        dependencies = set()
        for title in [self.wiki.logo_page, self.wiki.menu_page]:
            if title not in self.storage:
                dependencies.add(werkzeug.url_quote(title))
        for title in [self.wiki.menu_page]:
            if title in self.storage:
                inode, size, mtime = self.storage.page_file_meta(title)
                etag = '%s/%d-%d' % (werkzeug.url_quote(title), inode, mtime)
                dependencies.add(etag)
        return dependencies

class WikiPageText(WikiPage):
    """Pages of mime type text/* use this for display."""

    def content_iter(self, lines):
        yield '<pre>'
        for line in lines:
            yield werkzeug.html(line)
        yield '</pre>'

    def plain_text(self):
        """
        Get the content of the page with all markup removed, used for
        indexing.
        """

        return self.storage.page_text(self.title)


    def view_content(self, lines=None):
        """Read the page content from storage or preview and return iterator."""

        if lines is None:
            f = self.storage.open_page(self.title)
            lines = self.storage.page_lines(f)
        return self.content_iter(lines)

    def editor_form(self, preview=None):
        """Generate the HTML for the editor."""

        author = self.request.get_author()
        lines = []
        try:
            page_file = self.storage.open_page(self.title)
            lines = self.storage.page_lines(page_file)
            (rev, old_date, old_author,
                old_comment) = self.storage.page_meta(self.title)
            comment = _(u'modified')
            if old_author == author:
                comment = old_comment
        except NotFoundErr:
            comment = _(u'created')
            rev = -1
        except ForbiddenErr, e:
            yield werkzeug.html.p(
                werkzeug.html(_(unicode(e))))
            return
        if preview:
            lines = preview
            comment = self.request.form.get('comment', comment)
        html = werkzeug.html
        yield u'<form action="" method="POST" class="editor"><div>'
        yield u'<textarea name="text" cols="80" rows="20" id="editortext">'
        for line in lines:
            yield werkzeug.escape(line)
        yield u"""</textarea>"""
        yield html.input(type_="hidden", name="parent", value=rev)
        yield html.label(html(_(u'Comment')), html.input(name="comment",
            value=comment), class_="comment")
        yield html.label(html(_(u'Author')), html.input(name="author",
            value=self.request.get_author()), class_="comment")
        yield html.div(
                html.input(type_="submit", name="save", value=_(u'Save')),
                html.input(type_="submit", name="preview", value=_(u'Preview')),
                html.input(type_="submit", name="cancel", value=_(u'Cancel')),
                class_="buttons")
        yield u'</div></form>'
        if preview:
            yield html.h1(html(_(u'Preview, not saved')), class_="preview")
            for part in self.view_content(preview):
                yield part

    def diff_content(self, from_text, to_text, message=u''):
        """Generate the HTML markup for a diff."""

        def infiniter(iterator):
            """Turn an iterator into an infinite one, padding it with None"""

            for i in iterator:
                yield i
            while True:
                yield None

        diff = difflib._mdiff(from_text.split('\n'), to_text.split('\n'))
        stack = []
        mark_re = re.compile('\0[-+^]([^\1\0]*)\1|([^\0\1])')
        yield message
        yield u'<pre class="diff">'
        for old_line, new_line, changed in diff:
            old_no, old_text = old_line
            new_no, new_text = new_line
            line_no = (new_no or old_no or 1)-1
            if changed:
                yield u'<div class="change" id="line_%d">' % line_no
                old_iter = infiniter(mark_re.finditer(old_text))
                new_iter = infiniter(mark_re.finditer(new_text))
                old = old_iter.next()
                new = new_iter.next()
                buff = u''
                while old or new:
                    while old and old.group(1):
                        if buff:
                            yield werkzeug.escape(buff)
                            buff = u''
                        yield u'<del>%s</del>' % werkzeug.escape(old.group(1))
                        old = old_iter.next()
                    while new and new.group(1):
                        if buff:
                            yield werkzeug.escape(buff)
                            buff = u''
                        yield u'<ins>%s</ins>' % werkzeug.escape(new.group(1))
                        new = new_iter.next()
                    if new:
                        buff += new.group(2)
                    old = old_iter.next()
                    new = new_iter.next()
                if buff:
                    yield werkzeug.escape(buff)
                yield u'</div>'
            else:
                yield u'<div class="orig" id="line_%d">%s</div>' % (
                    line_no, werkzeug.escape(old_text))
        yield u'</pre>'

class WikiPageColorText(WikiPageText):
    """Text pages, but displayed colorized with pygments"""

    def view_content(self, lines=None):
        """Generate HTML for the content."""

        if lines is None:
            text = self.storage.page_text(self.title)
        else:
            text = ''.join(lines)
        return self.highlight(text, mime=self.mime)

    def highlight(self, text, mime=None, syntax=None, line_no=0):
        """Colorize the source code."""

        if pygments is None:
            yield werkzeug.html.pre(werkzeug.html(text))
            return

        formatter = pygments.formatters.HtmlFormatter()
        formatter.line_no = line_no

        def wrapper(source, outfile):
            """Wrap each line of formatted output."""

            yield 0, '<div class="highlight"><pre>'
            for lineno, line in source:
                yield (lineno,
                       werkzeug.html.span(line, id_="line_%d" %
                                         formatter.line_no))
                formatter.line_no += 1
            yield 0, '</pre></div>'

        formatter.wrap = wrapper
        try:
            if mime:
                lexer = pygments.lexers.get_lexer_for_mimetype(mime)
            elif syntax:
                lexer = pygments.lexers.get_lexer_by_name(syntax)
            else:
                lexer = pygments.lexers.guess_lexer(text)
        except pygments.util.ClassNotFoundErr:
            yield werkzeug.html.pre(werkzeug.html(text))
            return
        html = pygments.highlight(text, lexer, formatter)
        yield html

class WikiPageWiki(WikiPageColorText):
    """Pages of with wiki markup use this for display."""

    def __init__(self, *args, **kw):
        super(WikiPageWiki, self).__init__(*args, **kw)
        if self.config.get_bool('wiki_words', False):
            self.parser = WikiWikiParser
        else:
            self.parser = WikiParser
        if self.config.get_bool('ignore_indent', False):
            try:
                del self.parser.block['indent']
            except KeyError:
                pass

    def extract_links(self, text=None):
        """Extract all links from the page."""

        if text is None:
            try:
                text = self.storage.page_text(self.title)
            except NotFoundErr:
                text = u''
        return self.parser.extract_links(text)

    def view_content(self, lines=None):
        if lines is None:
            f = self.storage.open_page(self.title)
            lines = self.storage.page_lines(f)
        if self.wiki.icon_page and self.wiki.icon_page in self.storage:
            icons = self.index.page_links_and_labels(self.wiki.icon_page)
            smilies = dict((emo, link) for (link, emo) in icons)
        else:
            smilies = None
        content = self.parser(lines, self.wiki_link, self.wiki_image,
                             self.highlight, self.wiki_math, smilies)
        return content

    def wiki_math(self, math):
        math_url = self.config.get('math_url',
                            'http://www.mathtran.org/cgi-bin/mathtran?tex=')
        if '%s' in math_url:
            url = math_url % werkzeug.url_quote(math)
        else:
            url = '%s%s' % (math_url, werkzeug.url_quote(math))
        label = werkzeug.escape(math, quote=True)
        return werkzeug.html.img(src=url, alt=label, class_="math")

    def dependencies(self):
        dependencies = WikiPage.dependencies(self)
        for title in [self.wiki.icon_page]:
            if title in self.storage:
                inode, size, mtime = self.storage.page_file_meta(title)
                etag = '%s/%d-%d' % (werkzeug.url_quote(title), inode, mtime)
                dependencies.add(etag)
        for link in self.index.page_links(self.title):
            if link not in self.storage:
                dependencies.add(werkzeug.url_quote(link))
        return dependencies

class WikiPageFile(WikiPage):
    """Pages of all other mime types use this for display."""

    def view_content(self, lines=None):
        if self.title not in self.storage:
            raise NotFoundErr()
        content = ['<p>Download <a href="%s">%s</a> as <i>%s</i>.</p>' %
                   (self.request.get_download_url(self.title),
                    werkzeug.escape(self.title), self.mime)]
        return content

    def editor_form(self, preview=None):
        author = self.request.get_author()
        if self.title in self.storage:
            comment = _(u'changed')
            (rev, old_date, old_author,
                old_comment) = self.storage.page_meta(self.title)
            if old_author == author:
                comment = old_comment
        else:
            comment = _(u'uploaded')
            rev = -1
        html = werkzeug.html
        yield html.p(html(
                _(u"This is a binary file, it can't be edited on a wiki. "
                  u"Please upload a new version instead.")))
        yield html.form(html.div(
            html.div(html.input(type_="file", name="data"), class_="upload"),
            html.input(type_="hidden", name="parent", value=rev),
            html.label(html(_(u'Comment')), html.input(name="comment",
                       value=comment)),
            html.label(html(_(u'Author')), html.input(name="author",
                       value=author)),
            html.div(html.input(type_="submit", name="save", value=_(u'Save')),
                     html.input(type_="submit", name="cancel",
                                value=_(u'Cancel')),
            class_="buttons")), action="", method="POST", class_="editor",
                                enctype="multipart/form-data")

class WikiPageImage(WikiPageFile):
    """Pages of mime type image/* use this for display."""

    render_file = '128x128.png'

    def view_content(self, lines=None):
        if self.title not in self.storage:
            raise NotFoundErr()
        content = ['<img src="%s" alt="%s">'
                   % (self.request.get_url(self.title, self.wiki.render),
                      werkzeug.escape(self.title))]
        return content

    def render_mime(self):
        """Give the filename and mime type of the rendered thumbnail."""

        if not Image:
            raise NotImplementedError('No Image library available')
        return  self.render_file, 'image/png'

    def render_cache(self, cache_dir):
        """Render the thumbnail and save in the cache."""

        if not Image:
            raise NotImplementedError('No Image library available')
        page_file = self.storage.open_page(self.title)
        cache_path = os.path.join(cache_dir, self.render_file)
        cache_file = open(cache_path, 'wb')
        try:
            im = Image.open(page_file)
            im = im.convert('RGBA')
            im.thumbnail((128, 128), Image.ANTIALIAS)
            im.save(cache_file,'PNG')
        except IOError:
            raise UnsupportedMediaTypeErr('Image corrupted')
        cache_file.close()
        return cache_path

class WikiPageCSV(WikiPageFile):
    """Display class for type text/csv."""

    def content_iter(self, lines=None):
        import csv
        # XXX Add preview support
        csv_file = self.storage.open_page(self.title)
        reader = csv.reader(csv_file)
        html_title = werkzeug.escape(self.title, quote=True)
        yield u'<table id="%s" class="csvfile">' % html_title
        try:
            for row in reader:
                yield u'<tr>%s</tr>' % (u''.join(u'<td>%s</td>' % cell
                                                 for cell in row))
        except csv.Error, e:
            yield u'</table>'
            yield werkzeug.p(werkzeug.html(
                _(u'Error parsing CSV file %{file}s on line %{line}d: %{error}s')
                % {'file': html_title, 'line': reader.line_num, 'error': e}))
        finally:
            csv_file.close()
        yield u'</table>'

    def view_content(self, lines=None):
        if self.title not in self.storage:
            raise NotFoundErr()
        return self.content_iter(lines)

class WikiPageRST(WikiPageText):
    """
    Display ReStructured Text.
    """

    def content_iter(self, lines):
        try:
            from docutils.core import publish_parts
        except ImportError:
            return super(WikiPageRST, self).content_iter(lines)
        text = ''.join(lines)
        SAFE_DOCUTILS = dict(file_insertion_enabled=False, raw_enabled=False)
        content = publish_parts(text, writer_name='html',
                                settings_overrides=SAFE_DOCUTILS)['html_body']
        return [content]


class WikiPageBugs(WikiPageText):
    """
    Display class for type text/x-bugs
    Parse the ISSUES file in (roughly) format used by ciss
    """

    def content_iter(self, lines):
        last_lines = []
        in_header = False
        in_bug = False
        attributes = {}
        title = None
        for line_no, line in enumerate(lines):
            if last_lines and line.startswith('----'):
                title = ''.join(last_lines)
                last_lines = []
                in_header = True
                attributes = {}
            elif in_header and ':' in line:
                attribute, value = line.split(':', 1)
                attributes[attribute.strip()] = value.strip()
            else:
                if in_header:
                    if in_bug:
                        yield '</div>'
                    tags = [tag.strip() for tag in
                            attributes.get('tags', '').split()
                            if tag.strip()]
                    yield '<div id="line_%d">' % (line_no)
                    in_bug = True
                    if title:
                        yield werkzeug.html.h2(werkzeug.html(title))
                    if attributes:
                        yield '<dl>'
                        for attribute, value in attributes.iteritems():
                            yield werkzeug.html.dt(werkzeug.html(attribute))
                            yield werkzeug.html.dd(werkzeug.html(value))
                        yield '</dl>'
                    in_header = False
                if not line.strip():
                    if last_lines:
                        if last_lines[0][0] in ' \t':
                            yield werkzeug.html.pre(werkzeug.html(
                                            ''.join(last_lines)))
                        else:
                            yield werkzeug.html.p(werkzeug.html(
                                            ''.join(last_lines)))
                        last_lines = []
                else:
                    last_lines.append(line)
        if last_lines:
            if last_lines[0][0] in ' \t':
                yield werkzeug.html.pre(werkzeug.html(
                                ''.join(last_lines)))
            else:
                yield werkzeug.html.p(werkzeug.html(
                                ''.join(last_lines)))
        if in_bug:
            yield '</div>'


class WikiTitleConverter(werkzeug.routing.PathConverter):
    """Behaves like the path converter, except that it escapes slashes."""

    def to_url(self, value):
        return werkzeug.url_quote(value.strip(), self.map.charset, safe="")

    regex='([^+%]|%[^2]|%2[^Bb]).*'

class WikiAllConverter(werkzeug.routing.BaseConverter):
    """Matches everything."""

    regex='.*'


class Wiki(object):
    """
    The main class of the wiki, handling initialization of the whole
    application and most of the logic.
    """
    storage_class = WikiStorage
    index_class = WikiSearch
    filename_map = {
        'README': (WikiPageText, 'text/plain'),
        'ISSUES': (WikiPageBugs, 'text/x-bugs'),
        'ISSUES.txt': (WikiPageBugs, 'text/x-bugs'),
        'COPYING': (WikiPageText, 'text/plain'),
        'CHANGES': (WikiPageText, 'text/plain'),
        'MANIFEST': (WikiPageText, 'text/plain'),
        'favicon.ico': (WikiPageImage, 'image/x-icon'),
    }
    mime_map = {
        'text': WikiPageColorText,
        'application/x-javascript': WikiPageColorText,
        'application/x-python': WikiPageColorText,
        'text/csv': WikiPageCSV,
        'text/x-rst': WikiPageRST,
        'text/x-wiki': WikiPageWiki,
        'image': WikiPageImage,
        '': WikiPageFile,
    }
    icon = base64.b64decode(
'iVBORw0KGgoAAAANSUhEUgAAABAAAAAQCAYAAAAf8/9hAAAABHNCSVQICAgIfAhki'
'AAAAAlwSFlzAAAEnQAABJ0BfDRroQAAABl0RVh0U29mdHdhcmUAd3d3Lmlua3NjYXBlLm9yZ5vuPBo'
'AAALWSURBVDiNbdNLaFxlFMDx//fd19x5JdNJm0lIImPaYm2MfSUggrssXBVaChUfi1JwpQtxK7gqu'
'LMbQQQ3bipU0G3Rgg98DBpraWob00kzM6Z5TF7tdObm3vvd46K0TBo/OLtzfnychxIRut+Zo2/19vT'
'kLxXze6biONbGJMRipL39MJyt33rvp+rVT7rzVTfw2vFzLxwcLf/V7oSq1W4hACIkIigUtnaoNecXG'
'2u14T8blQRAd2v7yyN/RLFR6IRM1iedSeFnUvhpDydlI9ow0lcedG3348c1djeQz+WcThjgYZMgGBG'
'SJMEYgzGGODLEoTBYGH4DeHcXoDSSzaRVogQjyaMwhtgYcoUco+Nl5qbnubFw7fr//uB2tXp78uj4c'
'0YJsSTESUxsDCemjjH6YhnbtbA8xaVv7n/0uGZHDx48aH8+17iLJQrf9vCdFL7tkcn7/Pb7r8zdmWP'
'2zqwopa7sAl4/cV4NlvrPbgch7aBN1vUIOw9ZWmmw2dqkb18fQSegOrOgfD9zahfQ37/3su+ljj1T6'
'uCnAyxtoZVGa41tWSilULWfCZdaPD986MsjQxOHdwC9PdmT2tLk0oozpxfYf2SZwp4Iz1X4UZWBe1+'
'z9+5X+OkiruWpYr744ZMmvjn5dvrwoVHLdRzWtobY2Kwx9soyz5ZXuV9fQ5pXCBabXKuXcBwbYwxYe'
'kIppTXAF5VP2xutrVYmm8bzM1z9foSZik1z1SWMNLW1AtMrB/gnnMJxbSxbUV2a/QHQT8Y4c+vvC8V'
'C74VCoZcodvnxux5Msg+THCSKHy2R48YgIb/crITrreZlEYl33MKrYycvvnx88p2BUkkpRyGSEBmDi'
'WI6QcC95UUqM9PBzdqN99fbzc9EJNwBKKUoFw+8NDY8/sFQ/8CE57l5pZRdX6kHqxurW43mv98urM9'
'fjJPouohE8NQ1dkEayAJ5wAe2gRawJSKmO/c/aERMn5m9/ksAAAAASUVORK5CYII=')
    scripts = r"""function hatta_dates(){var a=document.getElementsByTagName(
'abbr');var p=function(i){return('00'+i).slice(-2)};for(var i=0;i<a.length;++i)
{var n=a[i];if(n.className==='date'){var m=
/^([0-9]{4})-([0-9]{2})-([0-9]{2})T([0-9]{2}):([0-9]{2}):([0-9]{2})Z$/.exec(
n.getAttribute('title'));var d=new Date(Date.UTC(+m[1],+m[2]-1,+m[3],+m[4],
+m[5],+m[6]));if(d){var b=-d.getTimezoneOffset()/60;if(b>=0){b="+"+b}
n.textContent=""+d.getFullYear()+"-"+p(d.getMonth()+1)+"-"+p(d.getDate())+" "+
p(d.getHours())+":"+p(d.getMinutes())+" GMT"+b}}}}function hatta_edit(){var b=
document.getElementById('editortext');if(b){var c=0+
document.location.hash.substring(1);var d=b.textContent.match(/(.*\n)/g);var
f='';for(var i=0;i<d.length&&i<c;++i){f+=d[i]}b.focus();if(b.setSelectionRange)
{b.setSelectionRange(f.length,f.length)}else if(b.createTextRange){var g=
b.createTextRange();g.collapse(true);g.moveEnd('character',f.length);
g.moveStart('character',f.length);g.select()}var h=document.createElement('pre'
);b.parentNode.appendChild(h);var k=window.getComputedStyle(b,'');h.style.font=
k.font;h.style.border=k.border;h.style.outline=k.outline;h.style.lineHeight=
k.lineHeight;h.style.letterSpacing=k.letterSpacing;h.style.fontFamily=
k.fontFamily;h.style.fontSize=k.fontSize;h.style.padding=0;h.style.overflow=
'scroll';try{h.style.whiteSpace="-moz-pre-wrap"}catch(e){};try{
h.style.whiteSpace="-o-pre-wrap"}catch(e){};try{h.style.whiteSpace="-pre-wrap"
}catch(e){};try{h.style.whiteSpace="pre-wrap"}catch(e){};h.textContent=f;
b.scrollTop=h.scrollHeight;h.parentNode.removeChild(h)}else{var l='';var m=
document.getElementsByTagName('link');for(var i=0;i<m.length;++i){var n=m[i];
if(n.getAttribute('type')==='application/wiki'){l=n.getAttribute('href')}}if(
l===''){return}var o=['p','h1','h2','h3','h4','h5','h6','pre','ul','div',
'span'];for(var j=0;j<o.length;++j){var m=document.getElementsByTagName(o[j]);
for(var i=0;i<m.length;++i){var n=m[i];if(n.id&&n.id.match(/^line_\d+$/)){
n.ondblclick=function(){var a=l+'#'+this.id.replace('line_','');
document.location.href=a}}}}}}
window.onload=function(){hatta_dates();hatta_edit()}"""
    style = """\
html { background: #fff; color: #2e3436;
    font-family: sans-serif; font-size: 96% }
body { margin: 1em auto; line-height: 1.3; width: 40em }
a { color: #3465a4; text-decoration: none }
a:hover { text-decoration: underline }
a.wiki:visited { color: #204a87 }
a.nonexistent, a.nonexistent:visited { color: #a40000; }
a.external { color: #3465a4; text-decoration: underline }
a.external:visited { color: #75507b }
a img { border: none }
img.math, img.smiley { vertical-align: middle }
pre { font-size: 100%; white-space: pre-wrap; word-wrap: break-word;
    white-space: -moz-pre-wrap; white-space: -pre-wrap;
    white-space: -o-pre-wrap; line-height: 1.2; color: #555753 }
div.conflict pre.local { background: #fcaf3e; margin-bottom: 0; color: 000}
div.conflict pre.other { background: #ffdd66; margin-top: 0; color: 000; border-top: #d80 dashed 1px; }
pre.diff div.orig { font-size: 75%; color: #babdb6 }
b.highlight, pre.diff ins { font-weight: bold; background: #fcaf3e;
color: #ce5c00; text-decoration: none }
pre.diff del { background: #eeeeec; color: #888a85; text-decoration: none }
pre.diff div.change { border-left: 2px solid #fcaf3e }
div.footer { border-top: solid 1px #babdb6; text-align: right }
h1, h2, h3, h4 { color: #babdb6; font-weight: normal; letter-spacing: 0.125em}
div.buttons { text-align: center }
input.button, div.buttons input { font-weight: bold; font-size: 100%;
    background: #eee; border: solid 1px #babdb6; margin: 0.25em; color: #888a85}
.history input.button { font-size: 75% }
.editor textarea { width: 100%; display: block; font-size: 100%;
    border: solid 1px #babdb6; }
.editor label { display:block; text-align: right }
.editor .upload { margin: 2em auto; text-align: center }
form.search input.search, .editor label input { font-size: 100%;
    border: solid 1px #babdb6; margin: 0.125em 0 }
.editor label.comment input  { width: 32em }
a.logo { float: left; display: block; margin: 0.25em }
div.header h1 { margin: 0; }
div.content { clear: left }
form.search { margin:0; text-align: right; font-size: 80% }
div.snippet { font-size: 80%; color: #888a85 }
div.header div.menu { float: right; margin-top: 1.25em }
div.header div.menu a.current { color: #000 }
hr { background: transparent; border:none; height: 0;
     border-bottom: 1px solid #babdb6; clear: both }
blockquote { border-left:.25em solid #ccc; padding-left:.5em; margin-left:0}
abbr.date {border:none}
dt {font-weight: bold; float: left; }
dd {font-style: italic; }
"""

    def __init__(self, config):
        if config.get_bool('show_version', False):
            sys.stdout.write("Hatta %s\n" % __version__)
            sys.exit()
        self.dead = False
        self.config = config
        self.language = config.get('language', None)
        global _
        if self.language is not None:
            try:
                _ = gettext.translation('hatta', 'locale',
                                        languages=[self.language]).ugettext
            except IOError:
                _ = gettext.translation('hatta', fallback=True,
                                        languages=[self.language]).ugettext
        else:
            _ = gettext.translation('hatta', fallback=True).ugettext
        self.path = os.path.abspath(config.get('pages_path', 'docs'))
        self.page_charset = config.get('page_charset', 'utf-8')
        self.menu_page = self.config.get('menu_page', u'Menu')
        self.front_page = self.config.get('front_page', u'Home')
        self.logo_page = self.config.get('logo_page', u'logo.png')
        self.locked_page = self.config.get('locked_page', u'Locked')
        self.site_name = self.config.get('site_name', u'Hatta Wiki')
        self.read_only = self.config.get_bool('read_only', False)
        self.icon_page = self.config.get('icon_page', None)
        self.pygments_style = self.config.get('pygments_style', 'tango')
        self.subdirectories = self.config.get_bool('subdirectories', False)
        if self.subdirectories:
            self.storage = WikiSubdirectoryStorage(self.path, self.page_charset)
        else:
            self.storage = self.storage_class(self.path, self.page_charset)
        self.cache = config.get('cache_path', None)
        if self.cache is None:
            self.cache = os.path.join(self.storage.repo_path, '.hg', 'hatta', 'cache')
        self.cache = os.path.abspath(self.cache)
        if not os.path.isdir(self.cache):
            os.makedirs(self.cache)
            reindex = True
        else:
            reindex = False
        self.index = self.index_class(self.cache, self.language, self.storage)
        R = werkzeug.routing.Rule
        self.url_map = werkzeug.routing.Map([
            R('/', defaults={'title': self.front_page},
              endpoint=self.view, methods=['GET', 'HEAD']),
            R('/+edit/<title:title>', endpoint=self.edit, methods=['GET']),
            R('/+edit/<title:title>', endpoint=self.save, methods=['POST']),
            R('/+undo/<title:title>', endpoint=self.undo, methods=['POST']),
            R('/+history/', endpoint=self.recent_changes,
              methods=['GET', 'HEAD']),
            R('/+history/<title:title>/<int:from_rev>:<int:to_rev>',
              endpoint=self.diff, methods=['GET', 'HEAD']),
            R('/+history/<title:title>/<int:rev>', endpoint=self.revision,
              methods=['GET', 'HEAD']),
            R('/+history/<title:title>', endpoint=self.history,
              methods=['GET', 'HEAD']),
            R('/+version/', endpoint=self.version, methods=['GET', 'HEAD']),
            R('/+version/<title:title>', endpoint=self.version,
              methods=['GET', 'HEAD']),
            R('/+download/<title:title>', endpoint=self.download,
              methods=['GET', 'HEAD']),
            R('/+render/<title:title>', endpoint=self.render,
              methods=['GET', 'HEAD']),
            R('/<title:title>', endpoint=self.view, methods=['GET', 'HEAD']),
            R('/+feed/rss', endpoint=self.rss, methods=['GET', 'HEAD']),
            R('/+feed/atom', endpoint=self.atom, methods=['GET', 'HEAD']),
            R('/+index', endpoint=self.all_pages, methods=['GET', 'HEAD']),
            R('/+orphaned', endpoint=self.orphaned, methods=['GET', 'HEAD']),
            R('/+wanted', endpoint=self.wanted, methods=['GET', 'HEAD']),
            R('/+search', endpoint=self.search, methods=['GET', 'POST']),
            R('/+search/<title:title>', endpoint=self.backlinks,
              methods=['GET', 'POST']),
            R('/off-with-his-head', endpoint=self.die, methods=['GET']),
            R('/+hg<all:path>', endpoint=self.hgweb, strict_slashes=False,
              methods=['GET', 'POST', 'HEAD']),
            # Pages with default content
            R('/favicon.ico', endpoint=self.favicon_ico,
              methods=['GET', 'HEAD']),
            R('/robots.txt', endpoint=self.robots_txt, methods=['GET', 'HEAD']),
            R('/+download/style.css', endpoint=self.style_css,
              methods=['GET', 'HEAD']),
            R('/+download/pygments.css', endpoint=self.pygments_css,
              methods=['GET', 'HEAD']),
            R('/+download/scripts.js', endpoint=self.scripts_js,
              methods=['GET', 'HEAD']),
        ], converters={'title':WikiTitleConverter, 'all':WikiAllConverter})

    def get_page(self, request, title):
        """Creates a page object based on page's mime type"""

        if title:
            try:
                page_class, mime = self.filename_map[title]
            except KeyError:
                mime = page_mime(title)
                major, minor = mime.split('/', 1)
                try:
                    page_class = self.mime_map[mime]
                except KeyError:
                    try:
                        plus_pos = minor.find('+')
                        if plus_pos>0:
                            minor_base = minor[plus_pos:]
                        else:
                            minor_base = ''
                        base_mime = '/'.join([major, minor_base])
                        page_class = self.mime_map[base_mime]
                    except KeyError:
                        try:
                            page_class = self.mime_map[major]
                        except KeyError:
                                page_class = self.mime_map['']
        else:
            page_class = WikiPage
            mime = ''
        return page_class(self, request, title, mime)

    def view(self, request, title):
        page = self.get_page(request, title)
        try:
            content = page.view_content()
        except NotFoundErr:
            url = request.get_url(title, self.edit, external=True)
            return werkzeug.routing.redirect(url, code=303)
        html = page.render_content(content)
        dependencies = page.dependencies()
        etag = '/(%s)' % u','.join(dependencies)
        return self.response(request, title, html, etag=etag)

    def revision(self, request, title, rev):
        text = self.storage.revision_text(title, rev)
        link = werkzeug.html.a(werkzeug.html(title),
                               href=request.get_url(title))
        content = [
            werkzeug.html.p(
                werkzeug.html(
                    _(u'Content of revision %(rev)d of page %(title)s:'))
                % {'rev': rev, 'title': link }),
            werkzeug.html.pre(werkzeug.html(text)),
        ]
        special_title = _(u'Revision of "%(title)s"') % {'title': title}
        page = self.get_page(request, title)
        html = page.render_content(content, special_title)
        response = self.response(request, title, html, rev=rev, etag='/old')
        return response

    def version(self, request, title=None):
        if title is None:
            version = self.storage.repo_revision()
        else:
            try:
                version, x, x, x = self.storage.page_history(title).next()
            except StopIteration:
                version = 0
        return werkzeug.Response('%d' % version, mimetype="text/plain")

    def _check_lock(self, title):
        restricted_pages = [
            'scripts.js',
            'robots.txt',
        ]
        if self.read_only:
            raise ForbiddenErr(_(u"This site is read-only."))
        if title in restricted_pages:
            raise ForbiddenErr(_(u"""Can't edit this page.
It can only be edited by the site admin directly on the disk."""))
        if title in self.index.page_links(self.locked_page):
            raise ForbiddenErr(_(u"This page is locked."))

    def save(self, request, title):
        self._check_lock(title)
        url = request.get_url(title)
        if request.form.get('cancel'):
            if title not in self.storage:
                url = request.get_url(self.front_page)
        if request.form.get('preview'):
            text = request.form.get("text")
            if text is not None:
                lines = text.split('\n')
            else:
                lines = [werkzeug.html.p(werkzeug.html(
                    _(u'No preview for binaries.')))]
            return self.edit(request, title, preview=lines)
        elif request.form.get('save'):
            comment = request.form.get("comment", "")
            author = request.get_author()
            text = request.form.get("text")
            try:
                parent = int(request.form.get("parent"))
            except (ValueError, TypeError):
                parent = None
            self.storage.reopen()
            self.index.update(self, request)
            page = self.get_page(request, title)
            if text is not None:
                if title == self.locked_page:
                    for link, label in page.extract_links(text):
                        if title == link:
                            raise ForbiddenErr(
                                _(u"This page is locked."))
                if u'href="' in comment or u'http:' in comment:
                    raise ForbiddenErr()
                if text.strip() == '':
                    self.storage.delete_page(title, author, comment)
                    url = request.get_url(self.front_page)
                else:
                    self.storage.save_text(title, text, author, comment, parent)
            else:
                text = u''
                upload = request.files['data']
                f = upload.stream
                if f is not None and upload.filename is not None:
                    try:
                        self.storage.save_file(title, f.tmpname, author,
                                               comment, parent)
                    except AttributeError:
                        self.storage.save_data(title, f.read(), author,
                                               comment, parent)
                else:
                    self.storage.delete_page(title, author, comment)
                    url = request.get_url(self.front_page)
            self.index.update_page(page, title, text=text)
        response = werkzeug.routing.redirect(url, code=303)
        response.set_cookie('author',
                            werkzeug.url_quote(request.get_author()),
                            max_age=604800)
        return response

    def edit(self, request, title, preview=None):
        self._check_lock(title)
        exists = title in self.storage
        if exists:
            self.storage.reopen()
        page = self.get_page(request, title)
        content = page.editor_form(preview)
        special_title = _(u'Editing "%(title)s"') % {'title': title}
        html = page.render_content(content, special_title)
        if not exists:
            response = werkzeug.Response(html, mimetype="text/html",
                                     status='404 Not found')

        elif preview:
            response = werkzeug.Response(html, mimetype="text/html")
        else:
            response = self.response(request, title, html, '/edit')
        response.headers.add('Cache-Control', 'no-cache')
        return response

    def atom(self, request):
        date_format = "%Y-%m-%dT%H:%M:%SZ"
        first_date = datetime.datetime.now()
        now = first_date.strftime(date_format)
        body = []
        first_title = u''
        count = 0
        unique_titles = {}
        for title, rev, date, author, comment in self.storage.history():
            if title in unique_titles:
                continue
            unique_titles[title] = True
            count += 1
            if count > 10:
                break
            if not first_title:
                first_title = title
                first_rev = rev
                first_date = date
            item = u"""<entry>
    <title>%(title)s</title>
    <link href="%(page_url)s" />
    <content>%(comment)s</content>
    <updated>%(date)s</updated>
    <author>
        <name>%(author)s</name>
        <uri>%(author_url)s</uri>
    </author>
    <id>%(url)s</id>
</entry>""" % {
                'title': werkzeug.escape(title),
                'page_url': request.adapter.build(self.view, {'title': title},
                                                  force_external=True),
                'comment': werkzeug.escape(comment),
                'date': date.strftime(date_format),
                'author': werkzeug.escape(author),
                'author_url': request.adapter.build(self.view,
                                                    {'title': author},
                                                    force_external=True),
                'url': request.adapter.build(self.revision,
                                             {'title': title, 'rev': rev},
                                             force_external=True),
            }
            body.append(item)
        content = u"""<?xml version="1.0" encoding="utf-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <title>%(title)s</title>
  <link rel="self" href="%(atom)s"/>
  <link href="%(home)s"/>
  <id>%(home)s</id>
  <updated>%(date)s</updated>
  <logo>%(logo)s</logo>
%(body)s
</feed>""" % {
            'title': self.site_name,
            'home': request.adapter.build(self.view, force_external=True),
            'atom': request.adapter.build(self.atom, force_external=True),
            'date': first_date.strftime(date_format),
            'logo': request.adapter.build(self.download,
                                          {'title': self.logo_page},
                                          force_external=True),
            'body': u''.join(body),
        }
        response = self.response(request, 'atom', content, '/atom',
                                 'application/xml', first_rev, first_date)
        response.set_etag('/atom/%d' % self.storage.repo_revision())
        response.make_conditional(request)
        return response

    def rss(self, request):
        """Serve an RSS feed of recent changes."""

        first_date = datetime.datetime.now()
        now = first_date.strftime("%a, %d %b %Y %H:%M:%S GMT")
        rss_body = []
        first_title = u''
        count = 0
        unique_titles = {}
        for title, rev, date, author, comment in self.storage.history():
            if title in unique_titles:
                continue
            unique_titles[title] = True
            count += 1
            if count > 10:
                break
            if not first_title:
                first_title = title
                first_rev = rev
                first_date = date
            item = (u'<item><title>%s</title><link>%s</link>'
                    u'<description>%s</description><pubDate>%s</pubDate>'
                    u'<dc:creator>%s</dc:creator><guid>%s</guid></item>' % (
                werkzeug.escape(title),
                request.adapter.build(self.view, {'title': title},
                                                  force_external=True),
                werkzeug.escape(comment),
                date.strftime("%a, %d %b %Y %H:%M:%S GMT"),
                werkzeug.escape(author),
                request.adapter.build(self.revision,
                                      {'title': title, 'rev': rev})
            ))
            rss_body.append(item)
        rss_head = u"""<?xml version="1.0" encoding="utf-8"?>
<rss version="2.0"
xmlns:dc="http://purl.org/dc/elements/1.1/"
xmlns:atom="http://www.w3.org/2005/Atom"
>
<channel>
    <title>%s</title>
    <atom:link href="%s" rel="self" type="application/rss+xml" />
    <link>%s</link>
    <description>%s</description>
    <generator>Hatta Wiki</generator>
    <language>en</language>
    <lastBuildDate>%s</lastBuildDate>

""" % (
            werkzeug.escape(self.site_name),
            request.adapter.build(self.rss),
            request.adapter.build(self.recent_changes),
            werkzeug.escape(_(u'Track the most recent changes to the wiki '
                              u'in this feed.')),
            first_date,
        )
        content = [rss_head]+rss_body+[u'</channel></rss>']
        response = self.response(request, 'rss', content, '/rss',
                                 'application/xml', first_rev, first_date)
        response.set_etag('/rss/%d' % self.storage.repo_revision())
        response.make_conditional(request)
        return response

    def response(self, request, title, content, etag='', mime='text/html',
                 rev=None, date=None, size=None):
        """Create a WikiResponse for a page."""

        response = WikiResponse(content, mimetype=mime)
        if rev is None:
            inode, _size, mtime = self.storage.page_file_meta(title)
            response.set_etag(u'%s/%s/%d-%d' % (etag, werkzeug.url_quote(title),
                                                inode, mtime))
            if size == -1:
                size = _size
        else:
            response.set_etag(u'%s/%s/%s' % (etag, werkzeug.url_quote(title),
                                             rev))
        if size:
            response.content_length = size
        response.make_conditional(request)
        return response

    def download(self, request, title):
        """Serve the raw content of a page directly from disk."""

        mime = page_mime(title)
        if mime == 'text/x-wiki':
            mime = 'text/plain'
        try:
            wrap_file = werkzeug.wrap_file
        except AttributeError:
            wrap_file = lambda x, y:y
        f = wrap_file(request.environ, self.storage.open_page(title))
        response = self.response(request, title, f, '/download', mime, size=-1)
        response.direct_passthrough = True
        return response

    def render(self, request, title):
        """Serve a thumbnail or otherwise rendered content."""

        def file_time_and_size(file_path):
            """Get file's modification timestamp and its size."""

            try:
                (st_mode, st_ino, st_dev, st_nlink, st_uid, st_gid, st_size,
                 st_atime, st_mtime, st_ctime) = os.stat(file_path)
            except OSError:
                st_mtime = 0
                st_size = None
            return st_mtime, st_size

        def rm_temp_dir(dir_path):
            """Delete the directory with subdirectories."""

            for root, dirs, files in os.walk(dir_path, topdown=False):
                for name in files:
                    try:
                        os.remove(os.path.join(root, name))
                    except OSError:
                        pass
                for name in dirs:
                    try:
                        os.rmdir(os.path.join(root, name))
                    except OSError:
                        pass
            try:
                os.rmdir(dir_path)
            except OSError:
                pass

        page = self.get_page(request, title)
        try:
            cache_filename, cache_mime = page.render_mime()
            render = page.render_cache
        except (AttributeError, NotImplementedError):
            return self.download(request, title)

        cache_dir = os.path.join(self.cache, 'render',
                                  werkzeug.url_quote(title, safe=''))
        cache_file = os.path.join(cache_dir, cache_filename)
        page_inode, page_size, page_mtime = self.storage.page_file_meta(title)
        cache_mtime, cache_size = file_time_and_size(cache_file)
        if page_mtime > cache_mtime:
            if not os.path.exists(cache_dir):
                os.makedirs(cache_dir)
            try:
                temp_dir = tempfile.mkdtemp(dir=cache_dir)
                result_file = render(temp_dir)
                mercurial.util.rename(result_file, cache_file)
            finally:
                rm_temp_dir(temp_dir)
        try:
            wrap_file = werkzeug.wrap_file
        except AttributeError:
            wrap_file = lambda x, y:y
        f = wrap_file(request.environ, open(cache_file))
        response = self.response(request, title, f, '/render', cache_mime,
                                 size=cache_size)
        response.direct_passthrough = True
        return response

    def undo(self, request, title):
        """Revert a change to a page."""

        self._check_lock(title)
        rev = None
        for key in request.form:
            try:
                rev = int(key)
            except ValueError:
                pass
        author = request.get_author()
        if rev is not None:
            try:
                parent = int(request.form.get("parent"))
            except (ValueError, TypeError):
                parent = None
            self.storage.reopen()
            self.index.update(self, request)
            if rev == 0:
                comment = _(u'Delete page %(title)s') % {'title': title}
                data = ''
                self.storage.delete_page(title, author, comment)
            else:
                comment = _(u'Undo of change %(rev)d of page %(title)s') % {
                    'rev': rev, 'title': title}
                data = self.storage.page_revision(title, rev-1)
                self.storage.save_data(title, data, author, comment, parent)
            page = self.get_page(request, title)
            self.index.update_page(page, title, data=data)
        url = request.adapter.build(self.history, {'title': title},
                                    method='GET', force_external=True)
        return werkzeug.redirect(url, 303)

    def history(self, request, title):
        """Display history of changes of a page."""

        page = self.get_page(request, title)
        content = page.render_content(page.history_list(),
            _(u'History of "%(title)s"') % {'title': title})
        response = self.response(request, title, content, '/history')
        return response


    def recent_changes(self, request):
        """Serve the recent changes page."""

        def changes_list(page):
            """Generate the content of the recent changes page."""

            h = werkzeug.html
            yield u'<ul>'
            last = {}
            lastrev = {}
            count = 0
            for title, rev, date, author, comment in self.storage.history():
                if (author, comment) == last.get(title, (None, None)):
                    continue
                count += 1
                if count > 100:
                    break
                if rev > 0:
                    date_url = request.adapter.build(self.diff, {
                        'title': title,
                        'from_rev': rev-1,
                        'to_rev': lastrev.get(title, rev)
                    })
                elif rev == 0:
                    date_url = request.adapter.build(self.revision, {
                        'title': title, 'rev': rev})
                else:
                    date_url = request.adapter.build(self.history, {
                        'title': title})
                last[title] = author, comment
                lastrev[title] = rev

                yield h.li(h.a(page.date_html(date), href=date_url), ' ',
                    h.b(page.wiki_link(title)), u' . . . . ',
                    h.i(page.wiki_link(author)),
                    h.div(h(comment), class_="comment")
                )
            yield u'</ul>'

        page = self.get_page(request, '')
        content = page.render_content(changes_list(page), _(u'Recent changes'))
        response = WikiResponse(content, mimetype='text/html')
        response.set_etag('/history/%d' % self.storage.repo_revision())
        response.make_conditional(request)
        return response

    def diff(self, request, title, from_rev, to_rev):
        """Show the differences between specified revisions."""

        page = self.get_page(request, title)
        build = request.adapter.build
        from_url = build(self.revision, {'title': title, 'rev': from_rev})
        to_url = build(self.revision, {'title': title, 'rev': to_rev})
        a = werkzeug.html.a
        links = {
            'link1': a(str(from_rev), href=from_url),
            'link2': a(str(to_rev), href=to_url),
            'link': a(werkzeug.html(title), href=request.get_url(title)),
        }
        message = werkzeug.html(_(
            u'Differences between revisions %(link1)s and %(link2)s '
            u'of page %(link)s.')) % links
        diff_content = getattr(page, 'diff_content', None)
        if diff_content:
            from_text = self.storage.revision_text(page.title, from_rev)
            to_text = self.storage.revision_text(page.title, to_rev)
            content = page.diff_content(from_text, to_text, message)
        else:
            content = [werkzeug.html.p(werkzeug.html(
                _(u"Diff not available for this kind of pages.")))]
        special_title = _(u'Diff for "%(title)s"') % {'title': title}
        html = page.render_content(content, special_title)
        response = werkzeug.Response(html, mimetype='text/html')
        return response


    def all_pages(self, request):
        """Show index of all pages in the wiki."""

        page = self.get_page(request, '')
        all_pages = sorted(self.storage.all_pages())
        content = page.pages_list(all_pages, _(u'Index of all pages'))
        html = page.render_content(content, _(u'Page Index'))
        response = WikiResponse(html, mimetype='text/html')
        response.set_etag('/+index/%d' % self.storage.repo_revision())
        response.make_conditional(request)
        return response

    def orphaned(self, request):
        """Show all pages that don't have backlinks."""

        page = self.get_page(request, '')
        pages = self.index.orphaned_pages()
        content = page.pages_list(pages,
                                  _(u'List of pages with no links to them'))
        html = page.render_content(content, _(u'Orphaned pages'))
        response = WikiResponse(html, mimetype='text/html')
        response.set_etag('/+orphaned/%d' % self.storage.repo_revision())
        response.make_conditional(request)
        return response

    def wanted(self, request):
        """Show all pages that don't exist yet, but are linked."""

        def wanted_pages_list(page):
            """Generate the content of wanted pages page."""

            h = werkzeug.html
            yield h.p(h(
                _(u"List of pages that are linked to, but don't exist yet.")))
            yield u'<ol class="wanted">'
            for refs, title in self.index.wanted_pages():
                url = page.get_url(title, self.backlinks)
                yield h.li(h.b(page.wiki_link(title)),
                           h.i(u' (', h.a(h(_(u"%d references") % refs),
                                          href=url, class_="backlinks"), ')'))
            yield u'</ol>'

        page = self.get_page(request, '')
        content = wanted_pages_list(page)
        html = page.render_content(content, _(u'Wanted pages'))
        response = WikiResponse(html, mimetype='text/html')
        response.set_etag('/+wanted/%d' % self.storage.repo_revision())
        response.make_conditional(request)
        return response

    def search(self, request):
        """Serve the search results page."""

        def search_snippet(title, words):
            """Extract a snippet of text for search results."""

            try:
                text = self.storage.page_text(title)
            except NotFoundErr:
                return u''
            regexp = re.compile(u"|".join(re.escape(w) for w in words),
                                re.U|re.I)
            match = regexp.search(text)
            if match is None:
                return u""
            position = match.start()
            min_pos = max(position - 60, 0)
            max_pos = min(position + 60, len(text))
            snippet = werkzeug.escape(text[min_pos:max_pos])
            highlighted = werkzeug.html.b(match.group(0), class_="highlight")
            html = regexp.sub(highlighted, snippet)
            return html

        def page_search(words, page, request):
            """Display the search results."""

            h = werkzeug.html
            self.storage.reopen()
            self.index.update(self, request)
            result = sorted(self.index.find(words), key=lambda x:-x[0])
            yield werkzeug.html.p(h(_(u'%d page(s) containing all words:')
                                  % len(result)))
            yield u'<ol class="search">'
            for number, (score, title) in enumerate(result):
                yield h.li(h.b(page.wiki_link(title)), u' ', h.i(str(score)),
                           h.div(search_snippet(title, words),
                                 _class="snippet"),
                           id_="search-%d" % (number+1))
            yield u'</ol>'

        query = request.values.get('q', u'').strip()
        page = self.get_page(request, '')
        if not query:
            url = request.get_url(view=self.all_pages, external=True)
            return werkzeug.routing.redirect(url, code=303)
        words = tuple(self.index.split_text(query, stop=False))
        if not words:
            words = (query,)
        title = _(u'Searching for "%s"') % u" ".join(words)
        content = page_search(words, page, request)
        html = page.render_content(content, title)
        return WikiResponse(html, mimetype='text/html')

    def backlinks(self, request, title):
        """Serve the page with backlinks."""

        self.storage.reopen()
        self.index.update(self, request)
        page = self.get_page(request, title)
        message = _(u'Pages that contain a link to %(link)s.')
        link = page.wiki_link(title)
        pages = self.index.page_backlinks(title)
        content = page.pages_list(pages, message, link, _class='backlinks')
        html = page.render_content(content, _(u'Links to "%s"') % title)
        response = WikiResponse(html, mimetype='text/html')
        response.set_etag('/+search/%d' % self.storage.repo_revision())
        response.make_conditional(request)
        return response

    def _serve_default(self, request, title, content, mime):
        """Some pages have their default content."""

        if title in self.storage:
            return self.download(request, title)
        response = werkzeug.Response(content, mimetype=mime)
        response.set_etag('/%s/-1' % title)
        response.make_conditional(request)
        return response

    def scripts_js(self, request):
        """Server the default scripts"""

        return self._serve_default(request, 'scripts.js', self.scripts,
                                   'text/javascript')

    def style_css(self, request):
        """Serve the default style"""

        return self._serve_default(request, 'style.css', self.style,
                                   'text/css')
    def pygments_css(self, request):
        """Serve the default pygments style"""

        if pygments is None:
            raise NotImplementedErr(_(u"Code highlighting is not available."))

        pygments_style = self.pygments_style
        if pygments_style not in pygments.styles.STYLE_MAP:
            pygments_style = 'default'
        formatter = pygments.formatters.HtmlFormatter(style=pygments_style)
        style_defs = formatter.get_style_defs('.highlight')
        return self._serve_default(request, 'pygments.css', style_defs,
                                   'text/css')

    def favicon_ico(self, request):
        """Serve the default favicon."""

        return self._serve_default(request, 'favicon.ico', self.icon,
                                   'image/x-icon')

    def robots_txt(self, request):
        """Serve the robots directives."""

        robots = ('User-agent: *\r\n'
                  'Disallow: /+*\r\n'
                  'Disallow: /%2B*\r\n'
                  'Disallow: /+edit\r\n'
                  'Disallow: /+feed\r\n'
                  'Disallow: /+history\r\n'
                  'Disallow: /+search\r\n'
                  'Disallow: /+hg\r\n'
                 )
        return self._serve_default(request, 'robots.txt', robots,
                                   'text/plain')

    def hgweb(self, request, path=None):
        """Serve the pages repository on the web like a normal hg repository."""

        if not self.config.get_bool('hgweb', False):
            raise ForbiddenErr(_(u'Repository access disabled.'))
        app = mercurial.hgweb.request.wsgiapplication(
            lambda: mercurial.hgweb.hgweb(self.storage.repo, self.site_name))
        def hg_app(env, start):
            env = request.environ
            prefix='/+hg'
            if env['PATH_INFO'].startswith(prefix):
                env["PATH_INFO"] = env["PATH_INFO"][len(prefix):]
                env["SCRIPT_NAME"] += prefix
            return app(env, start)
        return hg_app

    def die(self, request):
        """Terminate the standalone server if invoked from localhost."""

        if not request.remote_addr.startswith('127.'):
            raise ForbiddenErr(_(u'This URL can only be called locally.'))
        def agony():
            yield u'Oh dear!'
            self.dead = True
        return werkzeug.Response(agony(), mimetype='text/plain')

    @werkzeug.responder
    def application(self, environ, start):
        """The main application loop."""

        adapter = self.url_map.bind_to_environ(environ)
        request = WikiRequest(self, adapter, environ)
        try:
            try:
                endpoint, values = adapter.match()
                return endpoint(request, **values)
            except werkzeug.exceptions.HTTPException, err:
                return err
        finally:
            request.cleanup()
            del request
            del adapter

def read_config():
    """Read and parse the config."""

    config = WikiConfig(
        # Here you can modify the configuration: uncomment and change the ones
        # you need. Note that it's better use environment variables or command
        # line switches.

        # interface='',
        # port=8080,
        # pages_path = 'docs',
        # front_page = 'Home',
        # site_name = 'Hatta Wiki',
        # page_charset = 'UTF-8',
    )
    config.parse_args()
    config.parse_files()
    # config.sanitize()
    return config

def application(env, start):
    """Detect that we are being run as WSGI application."""

    global application
    config = read_config()
    script_dir = os.path.dirname(os.path.abspath(__file__))
    if config.get('pages_path') is None:
        config.set('pages_path', os.path.join(script_dir, 'docs'))
    wiki = Wiki(config)
    application = wiki.application
    return application(env, start)

def main(config=None, wiki=None):
    """Start a standalone WSGI server."""

    config = config or read_config()
    wiki = wiki or Wiki(config)
    app = wiki.application

    host, port = (config.get('interface', '0.0.0.0'),
                  int(config.get('port', 8080)))
    try:
        from cherrypy import wsgiserver
    except ImportError:
        try:
            from cherrypy import _cpwsgiserver as wsgiserver
        except ImportError:
            import wsgiref.simple_server
            server = wsgiref.simple_server.make_server(host, port, app)
            try:
                server.serve_forever()
            except KeyboardInterrupt:
                pass
            return
    apps = [('', app)]
    name = wiki.site_name
    server = wsgiserver.CherryPyWSGIServer((host, port), apps, server_name=name)
    try:
        server.start()
    except KeyboardInterrupt:
        server.stop()

if __name__ == "__main__":
    main()
