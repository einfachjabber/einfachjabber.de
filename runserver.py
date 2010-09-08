import os
os.environ['SBS_SETTINGS'] = '../development.py'
from einfachjabber import app
app.run(host='0.0.0.0')
