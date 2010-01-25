#!/usr/bin/python
#-*- coding: utf-8 -*-

import json, os.path
from werkzeug.exceptions import NotFound
from stepbystep.config import TUTORIAL_PATH

class Tutorial(object):
    """Functions necessary for the tutorial-viewer to work"""
    
    def gettutorial(self, id):
        """Load the tutorial specified by id from the .json file"""
        filename = TUTORIAL_PATH + id + '.json'
        if os.path.isfile(filename):
            with open(filename, 'r') as f:
                data = json.load(f)
            return data
        else:
            raise NotFound()
