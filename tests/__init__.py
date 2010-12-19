# -*- coding: utf-8 -*-
"""
    __init__.py
    ~~~~~~~~~~~~~~~~~~~~~~
    einfachjabber.de tests
"""

from flaskext.testing import TestCase as Base
from einfachjabber import create_app
from flask import Flask


class TestCase(Base):

    def create_app(self):
        return create_app('../testing.py')
