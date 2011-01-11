from flask import render_template

from einfachjabber.apps.stats import stats
from einfachjabber.apps.stats.helpers import pagesMonthly

@stats.route('/<date>')
def stats_index(date):
    data = pagesMonthly(date)
    return render_template('stats/index.html', data=data)
