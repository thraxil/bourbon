from wsgicollection import Collection
import simplejson
from sqlalchemy import and_
from md5 import md5

# some helpers
def _load_json(environ):
    try:
        entity = environ['wsgi.input'].read(int(environ['CONTENT_LENGTH']))
        struct = simplejson.loads(entity)
        return dict([(k.encode('us-ascii'), v) for k,v in struct.iteritems()])
    except ValueError:
        return dict()

def render_json(start_response, struct, headers=[],etag=None, environ={}):
    """ if etag is None, one will be generated as the md5 of the output.
    if one is passed in, make sure it's a quoted etag """
    body = simplejson.dumps(struct)
    if etag is None:
        etag = '"%s"' % md5(body).hexdigest()

    if etag == environ.get('HTTP_IF_NONE_MATCH', ''):
        start_response('304 Not Modified', [])
        return []
    
    start_response("200 OK", [('Content-Type', 'application/json'),
                              ('etag',etag)])
    return [body]

def get_id(environ):
    return environ['selector.vars']['id']

class Resource(Collection):
    """ A controller base class.

    wsgicollection delegates to the controllers derived from this class.

    It's mapping is:
    
      GET        None   list()
      POST       None   create()
      DELETE     id     delete()
      PUT        id     update()
      GET        id     retreive()
      GET        n/a    get_entry_form()  # Handles a GET/PUT/etc to /<id>;entry_form

     This class then provides basic CRUD functionality when it's connected to
     A SQLAlchemy table. It also makes it straightforward to override and add
     additional methods on the children.
    """


    domain_class = None
    id_column    = None
    parent       = None
    engine       = None

    def _session(self,environ):
        return environ['bourbon.session']

    def _get_id_column(self):
        """ figure out the id column for the class. defaults to the
        first primary key if none is specified """
        if self.id_column is None:
            return 'id'
        else:
            return self.id_column

    def _parent_clause(self,environ):
        """ if the class has parents, generate a where clause to include
        that selection criteria """
        if self.parent:
            return self.parent["column"] == environ['selector.vars'][self.parent["param"]]
        else:
            return None

    def _get_parent(self,environ):
        id = environ['selector.vars'][self.parent["param"]]
        pclass = self.parent["parent_class"]
        column = self.parent["parent_class_id_column"]
        s = self._session(environ)
        return s.query(pclass).selectone(column == id)

    def _fetch(self,environ):
        """ retrieve the object requested """
        s = self._session(environ)
        if self.parent == None:
            return s.query(self.domain_class).select_by(self._get_id_column() == get_id(environ))
        else:
            clause = and_(self.parent["column"] == self.parent["parent_class_id_column"],
                          self.parent["parent_class_id_column"] == environ['selector.vars'][self.parent["param"]],
                          self._get_id_column() == get_id(environ))
            return s.query(self.domain_class).select(clause)

    def _etag(self, environ):
        """ return an etag for this resource.

        override to generate custom "deep" etags. Otherwise, it will just
        do the full query on the object and return an md5 hash of the content that would
        normally be returned. That won't save you any CPU load, but it may reduce bandwidth.
        To reduce load, you really must override this function with something that quickly
        generates an etag.

        This should return a quoted etag.
        """
        return None

    def _collection_etag(self, environ):
        """
        returns an etag for the collection. same idea as above,
        but this is the one called by list() instead of retrieve().
        """
        return None

    # GET /
    def list(self,environ,start_response):
        """ invoked by wsgicollection when there's a GET request on the
        collection. returns a JSON representation in the standard collection
        structure. """
        etag = self._list_etag(environ)
        if etag == environ.get('HTTP_IF_NONE_MATCH', ''):
            start_response('304 Not Modified', [])
            return []
        
        s = self._session(environ)
        result = s.query(self.domain_class).select(self._parent_clause(environ)) #().execute()
        struct = {
            "members" : [{'href' : "%s" % getattr(row,self.id_column.name)}
                         for row in result],
            "next" : None}
        return render_json(start_response, struct, etag=etag, environ=environ)

    # POST /
    def create(self, environ, start_response):
        """ invoked by wsgicollection when there's a POST request to
        the base of the collection. it expects the POST request to contain
        a JSON representation of an object of the correct type to create.
        """
        id = self._create(environ)
        # rfc2616 sec 9.5
        # should respond with a 201 Created and an entity describing the status
        # and a location header
        start_response("201 Created", [("Location",str(id))])
        return []

    def _create(self,environ):
        """ create an object from a JSON representation in the request.
        if there isn't one, it just uses the id column info that it can
        deduce from the URL """
        struct = _load_json(environ)
        if not struct.has_key(self.id_column.name):
            struct[self.id_column.name] = get_id(environ)

        # if there's a parent, we need to make sure that
        # relationship gets included
        if self.parent:
            p = self._get_parent(environ)
            struct[self.parent["column"].name] = getattr(p,self.parent["parent_class_id_column"].name)
        s   = self._session(environ)
        obj = self.domain_class()
        for k in struct.keys():
            setattr(obj,k,struct[k])
        s.save(obj)
        return struct[self.id_column.name]


    # GET /{id}
    def retrieve(self, environ, start_response):
        """ invoked by a wsgicollection when a GET request is made for a resource
        in the collection. Fetches the resource object and returns a JSON representation
        of it. """

        # if there's a conditional request and it matches our etag,
        # respond to that
        etag   = self._etag(environ)
        if etag == environ.get('HTTP_IF_NONE_MATCH', ''):
            start_response('304 Not Modified', [])
            return []
        
        result = self._fetch(environ)[0]
        struct = dict()
        for k in result.c.keys():
            struct[k] = getattr(result,k)
        
        return render_json(start_response,struct,etag=etag,environ=environ)

    # PUT /{id}
    def update(self, environ, start_response):
        """ invoked by wsgicollection when a PUT request is made for a resource.
        updates the resource (or creates a new one) based on a JSON representation
        in the request body """

        # TODO: use etags to handle conditional PUT
        struct = _load_json(environ)
        r = self._fetch(environ)
        if r is not None and len(r) > 0:
            obj = r[0]
            for k in struct.keys():
                try:
                    setattr(obj,k,struct[k])
                except:
                    print "update failed on key %s" % k
#            self.table.update(self._get_id_column() == get_id(environ)).execute(struct)
            # rfc2616 s9.6
            start_response("204 OK",[])            
        else:
            # create a new one
            self._create(environ)
            # rfc2616 s9.6
            # a new resource was created, so we MUST respond with a 201
            start_response("201 Created",[])
        return []

    # DELETE /{id}
    def delete(self,environ, start_response):
        """ invoked by wsgicollection when a DELETE request is made for a resource.
        deletes the resource. """
        s = self._session(environ)
        obj = self._fetch(environ)[0]
        s.delete(obj)
        # rfc2616 section 9.7
        # since the response doesn't include an entity, respond with a 204: 
        start_response("204 No Content", [])
        return []

    # POST /{id}
    def post(self,environ,start_response):
        """ invoked by wsgicollection when a POST request is made to a resource.

        No default behavior can be specified. Hence, to be used, this method must
        be overridden. """
        # rfc2626 section 10.4.6
        start_response("405 Method Not Allowed",[('Allow','GET,PUT,DELETE')])
        yield []


