from setuptools import setup, find_packages

setup(
    name='einfachjabber',
    version='1.6',
    long_description=__doc__,
    packages=find_packages(),
    include_package_data=True,
    zip_safe=False,
    install_requires=[
        'cherrypy',
        'creoleparser',
        'Flask',
        'Flask-Mail',
        'Flask-Testing',
        'Flask-WTF',
        'markdown2',
        'piwik',
        'pygments',
        'pyyaml',
        'recaptcha-client',
        'simplejson',
        'xmpppy'
    ]
)
