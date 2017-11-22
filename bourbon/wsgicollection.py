import re

# Need a dispatcher the works on URI, method and content type
# Base is just URI
# Then a Collection which does URI, method and content-type (ala Java.0).
# other types of dispatching? 

COLL_MAP = {
    'GET': 'list',
    'POST': 'create'
    }

ENTRY_MAP = {
    'GET': 'retrieve',
    'PUT': 'update',
    'DELETE': 'delete',
    'POST' : 'post',
}

class Collection(object):
    """
     Create a Collection that presumes a URI parser that already has <id> and <noun> in 
     environ['selector.vars'] or environ['wsgi.url_vars'] 

     <noun> is the function name if present.
     <id> is used to key to an entry in the collection.
     Absence of <id> means to work on the collection itself.

      method     id     method
      ---------------------------------
      GET        None   list()
      POST       None   create()
      DELETE     id     delete()
      PUT        id     update()
      GET        id     retreive()
      GET        n/a    get_entry_form()  # Handles a GET/PUT/etc to /<id>;entry_form
      OPTIONS    None   keys(COLL_MAP)
#      OPTIONS    Id     keys(ENTRY_MAP) + dir()
    """

    def __call__(self, environ, start_response):
        print "call on ", self.__class__
        if 'wsgiorg.routing_args' in environ:
            url_vars = environ['wsgiorg.routing_args'][1]
        elif 'selector.vars' in environ:
            url_vars = environ['selector.vars']
        else:
            start_response("500 Internal Server Error", {'content-type': 'text/plain'})
            return ['Environment variables for wsgicollection.Collection not provided via WSGI.']

        id = url_vars.get('id', '')
        noun = url_vars.get('noun', '')
        method = environ['REQUEST_METHOD']

        function_name = "%s_%s" % (method.lower(), noun)
        if not noun:
            method_map = id and ENTRY_MAP or COLL_MAP
            function_name = method_map.get(method, '') 

        if function_name and not function_name.startswith("_") and function_name in dir(self):
            return getattr(self, function_name)(environ, start_response)
        else:
            start_response("404 Not Found", [("Content-Type", "text/plain")])
            print "tried to find %s on %s" % (function_name, self.__class__)
            return ["Resource not found."]



