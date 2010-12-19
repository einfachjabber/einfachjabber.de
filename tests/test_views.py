# -*- coding: utf-8 -*-
"""
    test_views.py
    ~~~~~~~~~~~~~~~~~~~~~~
    einfachjabber.de tests
"""

from einfachjabber.utils import *
from glob import glob
from os import chdir
from tests import TestCase
import re

class TestFrontend(TestCase):


    def test_pages(self):
        pages = ['',
                 'jabber',
                 'help',
                 'reg',
                 'oslist',
                 'impressum']
        for page in pages:
            rv = self.client.get('/' + page)
            self.assert_200(rv)

        rv = self.client.get('/notthere')
        self.assert_404(rv)

    def test_tutorial_images(self):
        rv = self.client.get('/static/tutorials/android-beem/android-beem1.png')
        self.assert_200(rv)


class TestData(TestCase):


    def test_tutorialdata(self):
        chdir(self.app.config['TUTORIAL_PATH'])
        files = glob('*.json')
        for file in files:
            tid = re.sub('.json', '', file)
            t = Tutorial()
            tut = t.gettutorial(tid)
