from setuptools import setup

setup(
    name='einfachjabber',
    version='1.5',
    long_description=__doc__,
    packages=['einfachjabber'],
    include_package_data=True,
    zip_safe=False,
    install_requires=[
        'cherrypy',
        'creoleparser',
        'Flask',
        'Flask-Mail',
        'Flask-WTF',
        'recaptcha-client',
        'simplejson',
        'xmpppy'
    ]
)
