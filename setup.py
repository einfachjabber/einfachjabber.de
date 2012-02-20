from setuptools import setup, find_packages

setup(
    name='einfachjabber',
    version='1.7.3.0',
    long_description=__doc__,
    packages=find_packages(),
    include_package_data=True,
    zip_safe=False,
    install_requires=[
        'cherrypy',
        'creoleparser',
        'Flask',
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
