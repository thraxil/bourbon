from sqlalchemy import create_session

def run_in_transaction(session,f,*args,**kwargs):
    r = []
    trans = session.create_transaction()
    try:
        r = f(*args,**kwargs)
        session.flush()
    except Exception, e:
        print "Exception: ", str(e)
        print "rolling back transaction"
        trans.rollback()
        return r
    trans.commit()
    return r


class BourbonApp(object):
    def __init__(self,urls,engine,config):
        self.urls = urls
        self.engine = engine
        self.config = config

    def __call__(self,environ,start_response):
        """ make the sqlalchemy session available to the controller
        and run the controller's method inside a transaction """
        environ['bourbon.engine'] = self.engine
        session = create_session(bind_to=self.engine)
        environ['bourbon.session'] = session
        environ['bourbon.config'] = self.config
        r = run_in_transaction(session, self.urls,environ,start_response)
        return r
        
