Bourbon
=======


Bourbon is a small framework designed to make it easy to develop and
deploy simple microapps. 

The idea is that you define a database model (with SQLAlchemy
currently) and some minimal controller classes that tie that model to
some url patterns (via Selector and WSGICollection) and the usual CRUD
methods are then accessible via HTTP. 

Current Features:

	* Basic HTTP method to -> CRUD mapping. 
	* JSON loading and rendering
	* automatic transaction support
	* strict adherence to rfc2616 (HTTP 1.1)
	* nested structures
	* paste deployment with .ini config files
	* paste template for "quickstart": paster create -t bourbon myapp

Todo:

	* use paste.fixture for more help with testing
	* content negotiation
	* command line tools for database init, etc.
	* better automatic figuring out of primary key columns and
	  parent-child relationships with the url mapping
        * more hooks to override the default behavior
	* abstract out ORM requirements so SQLObject or other
	  mappers can be used instead of SQLAlchemy
	* eliminate need for 'python setup.py develop' step
	* logging configuration

Example:
========

Say we want to create a very simple microapp that stores
articles, which each may belong to a category. We'll call our
app "storytime". 

We first use paster to create a skeleton bourbon project for us:

   $ paster create -t bourbon storytime

Enter whatever information you want when it prompts you. The result
will be a directory called 'storytime' with the following structure:

-------------------------------------
          /setup.py
	  /development.ini
	  /storytime.db
	  /storytime/
	  	    __init__.py
		    model.py
		    controllers.py
		    wsgiapp.py
-------------------------------------

Next we need to define our model in storytime/model.py. Add the
following to it:

-------------------------------------
# tables
category_table = Table('category', metadata,
                      Column('name', String(256), primary_key=True))

story_table = Table('story', metadata,
                  Column('slug',String(256), primary_key=True),
                  Column('title',String(256), index=True, nullable=False),
		  Column('author_name',String(256)),
		  Column('body',String(30000)),
		  Column('created',DateTime,default=datetime.now),
                  Column('category_name',String(256), ForeignKey('category.name')))

# domain classes
class Category(object):
    pass
class Story(object):
    pass

# mappers
categorymapper = mapper(Category,category_table,properties = {
    'stories' : relation(Story, cascade="all, delete-orphan",backref='category')})
storymapper    = mapper(Story,story_table)
----------------------------------------

Pretty basic. SQLAlchemy can be a bit verbose, but it's
straightforward. Note that the model contains nothing Bourbon
related. It's just a plain SQLAlchemy model and could be imported into
and used with anything else. 

storytime/controllers.py sets up the HTTP -> model mapping. We need to
create some controller objects and map them to urls. Add two
controller classes:

----------------------------------------
class CategoryCollection(Resource):
    domain_class = Category
    id_column    = Category.c.name

class StoryCollection(Resource):
    domain_class = Story
    id_column    = Story.c.slug
    parent       = dict(column                 = Story.c.category_name,
                        param                  = "categoryname",
                        parent_class           = Category,
                        parent_class_id_column = Category.c.name)
----------------------------------------

and then add two corresponding url mappers to the end:

----------------------------------------
urls.add('/[{id:word}][;{noun}]',                   _ANY_=CategoryCollection())
urls.add('/{categoryname}/[{id:word}][;{noun}][/]', _ANY_=StoryCollection())
----------------------------------------

This is best understood starting with the last couuple lines. Those
set up url mappings using selector, mapping all HTTP methods to
our controllers and putting a couple particular variables into the
WSGI environ so Bourbon can automatically construct/fetch the right
model objects. 

development.ini is a standard paste.deploy config file that
'paster serve' can run. Edit it to change the port number and/or the
database connection info (defaults to port 9080 and a sqlite database
named for the package).

#######################################
currently, it seems necessary to run

  $ python setup.py develop

to get the entry points picked up. I'm still not sure
why, but I hope to make that step not necessary
#######################################

You should now manually initalialize the database (commandline tools
for this are forthcoming):

  $ python
  >>> from storytime.model import *
  >>> engine = create_engine("sqlite:///storytime.db")
  >>> metadata.create_all(connectable=engine)

Then you can run the app with paster server:

  $ paster serve development.ini

And you now have HTTP+JSON access to the database on port 9080. So, eg.

  $ curl http://localhost:9080/
  {"members": [], "next": null}

add some categories:

  $ curl -X PUT http://localhost:9080/world
  $ curl -X PUT http://localhost:9080/local
  $ curl http://localhost:9080/
  {"members": [{"href": "world"}, {"href": "local"}], "next": null}

GET /world gets the category itself

  $ curl http://localhost:9080/world
  {"name": "world"}

while GET /world/ gets the collection of stories in the category
(currently none)

  $ curl http://localhost:9080/world/
  {"members": [], "next": null}

DELETE the local category:

  $ curl -X DELETE http://localhost:9080/local
  $ curl http://localhost:9080/     
  {"members": [{"href": "world"}], "next": null}


add a story to the world category

  $ curl -X PUT -d '{"title" : "World Peace Achieved", "author_name" : \
  "Dan Rather", "body" : "Yay!"}' http://localhost:9080/world/rather-world-peace

an alternate way to add a story:

  $ curl -X POST -d '{"title" : "Caffeinated Donuts Invented", "author_name" : \
  "Dan Rather", "body" : "Better than world peace!", "slug" : \
  "rather-donuts"}' http://localhost:9080/world/

The second approach uses a POST to the collection instead of a direct
PUT to the resource location. This is how you'll want to do it anytime
you use auto-generated keys, or if, eg, the slug was being
automatically generated from the title or something. 


In the style of the Atom API and Ruby on Rails' SimplyREST, you can
also define additional actions for controllers to respond to. That's
what the '{noun}' stuff in the url mapping was for. You just need to
add a method to the appropriate controller object with a name of
'<http method>_<noun>'. Eg, to respond to a GET request on
'/world;edit_form' you would add a method to CategoryCollection:

    def get_edit_form(self, environ, start_response):
        # make a form, call start_response() and
	# yield the content

Within that method, you may want to access the SQLAlchemy session and
the model object that the controller is mapped to. you can do that
with self._session() and self._fetch(environ) respectively. 

All methods are automatically wrapped in a transaction. Raising an
exception will cause it to rollback. 






