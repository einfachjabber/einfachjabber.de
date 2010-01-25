from cherrypy import wsgiserver
from manage import make_app

server = wsgiserver.CherryPyWSGIServer(('127.0.0.1', 9001), make_app())
try:
    server.start()
except KeyboardInterrupt:
    server.stop()
