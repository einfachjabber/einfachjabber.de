#!/usr/bin/python
#-*- coding: utf-8 -*-

import json
from stepbystep.config import TUTORIAL_PATH
from stepbystep.utils import url_map


def testjson(self):
    """docstring for testjson"""
    with open(TUTORIAL_PATH + 'windows-xp.json', 'r') as f:
        data = json.load(f)
    
    #numpages = len(data['tutorial'])
    #print data
    #print numpages
    #print data['tutorial']
