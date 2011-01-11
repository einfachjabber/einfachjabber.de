from flask import render_template

from einfachjabber.apps.stats import stats
from einfachjabber.apps.stats.helpers import pagesMonthly

@stats.route('/')
def stats_index():
    pages = pagesMonthly()
    return render_template('stats/index.html', pages=pages)
