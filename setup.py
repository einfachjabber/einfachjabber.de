from setuptools import setup, find_packages

setup(
    name='einfachjabber',
    version='1.7.4.5',
    long_description=__doc__,
    packages=find_packages(),
    include_package_data=True,
    zip_safe=False,
    install_requires=[
        'cherrypy',
        'creoleparser',
        'Flask==0.6.1',
        'Flask-CouchDB',
        'Flask-Mail',
        'Flask-Testing',
        'Flask-WTF',
        'markdown2',
        'piwik',
        'pydns',
        'pygments',
        'pyyaml',
        'simplejson',
        'xmpppy'
    ]
)
