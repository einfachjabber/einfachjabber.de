#!/usr/bin/python
#-*- coding: utf-8 -*-

import json
import os, glob, re
from werkzeug.exceptions import NotFound
from werkzeug.utils import cached_property
from stepbystep.config import TUTORIAL_PATH

class Clients(object):
    """Functions for managing the client-chooser"""

    def __init__(self, osystem):
        self.osystem = osystem

    @cached_property
    def clientlist(self):
        """reads the list of clients from the tutorial directory"""
        clist = []
        os.chdir(TUTORIAL_PATH)
        files = glob.glob(self.osystem + '-*.json')
        if not files:
            raise NotFound()
        for file in files:
            with open(file, 'r') as f:
                try:
                    clname = json.load(f)['client']
                    clist = clist + [clname]
                except:
                    errormail('Error in JSON-Data')
                    raise NotFound()
        return clist
