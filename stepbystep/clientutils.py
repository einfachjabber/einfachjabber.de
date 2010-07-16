#!/usr/bin/python
#-*- coding: utf-8 -*-

import json
import os, glob, re
from stepbystep import app

class Clients():
    """Functions for managing the client-chooser"""

    def clientlist(self, osystem):
        """reads the list of clients from the tutorial directory"""
        clist = []
        os.chdir(app.config['TUTORIAL_PATH'])
        files = glob.glob(osystem + '-*.json')
        if not files:
            abort(404)
        for file in files:
            with open(file, 'r') as f:
                try:
                    clname = json.load(f)['client']
                    clist = clist + [clname]
                except:
                    errormail('Error in JSON-Data')
                    abort(404)
        return clist
