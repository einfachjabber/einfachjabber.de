#!/usr/bin/python
#-*- coding: utf-8 -*-
from werkzeug import script

def make_app():
    from stepbystep.application import Stepbystep
    return Stepbystep()

action_runserver = script.make_runserver(make_app, use_reloader=True, use_debugger=True, use_evalex=True)

if __name__ == '__main__':
    script.run()
