#!/usr/bin/python
#-*- coding: utf-8 -*-

import json 
import os.path
from werkzeug.exceptions import NotFound
from werkzeug.utils import cached_property
from stepbystep.config import TUTORIAL_PATH

class Tutorial(object):
    """Functions necessary for the tutorial-viewer to work"""

    def __init__(self, id):
        self.id = id

    @cached_property
    def gettutorial(self):
        """Load the tutorial specified by id from the .json file"""
        filename = TUTORIAL_PATH + self.id + '.json'
        if os.path.isfile(filename):
            with open(filename, 'r') as f:
                data = json.load(f)
            return data
        else:
            raise NotFound()

    def pagination(self, page, maxpage):
        """pagination helper"""
        flpage = 1
        if page == 0:
            flpage = 0
        elif page == maxpage:
            flpage = 2
        elif page > maxpage:
            raise NotFound()
        return flpage

