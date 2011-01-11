from piwik import PiwikAPI

def pagesMonthly(date):
    piwik = PiwikAPI("http://stats.firefly-it.de/", "anonymous")
    tutorials = piwik.call(
                'Actions.getPageUrls',
                params = {
                    'idSite': 5,
                    'period': 'month',
                    'date': date,
                    'expanded': 1
                }
            )
    for tutorial in tutorials:
        if tutorial['label'] == 'tutorial':
            subtable = tutorial['idsubdatatable']
    pages = piwik.call(
                'Actions.getPageUrls',
                params = {
                    'idSite': 5,
                    'period': 'month',
                    'date': date,
                    'idSubtable': subtable,
                    'expanded': 1
                }
            )
    print pages
    data = []
    for page in pages:
        if page['label'] != '/index':
            for subtable in page['subtable']:
                if subtable['label'] == '/links':
                    endpagevisits = subtable['nb_visits']
            data.append({'label': page['label'],
                        'visits': page['nb_visits'],
                        'endpagevisits': endpagevisits
                        })
    return data
