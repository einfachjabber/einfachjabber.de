from einfachjabber import create_app
app = create_app('../development.py')
app.run(host='0.0.0.0')
