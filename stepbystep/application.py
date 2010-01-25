from werkzeug import Request, Response, SharedDataMiddleware, ClosingIterator
from werkzeug.exceptions import HTTPException, NotFound

from stepbystep.utils import url_map, local, local_manager
from stepbystep.config import STATIC_PATH
from stepbystep import views



class Stepbystep(object):

    def __init__(self):
        self.dispatch = SharedDataMiddleware(self.dispatch, {
            '/static': STATIC_PATH
        })

    def dispatch(self, environ, start_response):
        local.application = self
        # create a new request object by passing our environ to Request 
        # constructor
        request = Request(environ)
        # bind url map to current request
        local.url_adapter = adapter = url_map.bind_to_environ(request.environ)
        try:
            # get endpoint and variables of adapter
            # if it fails it will raise a NotFound catched
            endpoint, values = adapter.match()
            handler = getattr(views, endpoint)
            response = handler(request, **values)
        except NotFound, e:
            response = Response("Not found!")
            response.status_code = 404
        except HTTPException, e:
            response = e
        return ClosingIterator(response(environ, start_response),
                              [local_manager.cleanup])


    def __call__(self, environ, start_response):
        return self.dispatch(environ, start_response)
