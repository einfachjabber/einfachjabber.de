# -*- coding: utf-8 -*-
"""
    test_stepbystep
    ~~~~~~~~~~~~~~~

    :copyright: (c) 2010 by Benjamin Zimmer.
    :license: MIT, see LICENSE for more details.
"""

# -*- coding: utf-8 -*-
from os import chdir
from glob import glob
import re
import stepbystep
import unittest
import tempfile

class StepbystepTestCase(unittest.TestCase):

    def setUp(self):
        self.app = stepbystep.app.test_client()

    def tearDown(self):
        pass

    def test_oslist(self):
        rv = self.app.get('/oslist')
        assert '<ul id="oslist">' in rv.data
        assert '<div id="footer"' in rv.data

    def test_jsondata(self):
        chdir(stepbystep.app.config['TUTORIAL_PATH'])
        files = glob('*.json')
        for file in files:
            print file
            tid = re.sub('.json', '', file)
            rv = self.app.get('/tutorial/' + tid + '/')
            #print tid
            #print rv.data
            #assert str(tid) in rv.data
            #print(tid)

if __name__ == '__main__':
    unittest.main()
