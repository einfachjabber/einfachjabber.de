from piwik import PiwikAPI

def pagesMonthly():
    piwik = PiwikAPI("http://stats.firefly-it.de/", "anonymous")
    pages = piwik.call(
                'Actions.getPageUrls',
                params = {
                    'idSite': 5,
                    'period': 'month',
                    'date': 'today',
                    'idSubtable': 163
                }
            )
    return pages
