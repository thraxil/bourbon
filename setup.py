from setuptools import setup, find_packages

setup(
    name="bourbon",
    version="0.1",
    description="WSGI + Paste + SQLAlchemy based microapp framework",
    author="Anders Pearson",
    author_email="anders@columbia.edu",
    #url=url,
    #download_url=download_url,
    license="GPL",
    
    install_requires = [
        "SQLAlchemy","wsgiref >= 0.1.2", "selector >= 0.8.11",
        "simplejson >= 1.4", "nose >= 0.9.1", "PasteScript > 0.9.7",
        "Paste >= 0.9.7", "PasteDeploy >= 0.9.7",
    ],
#    scripts = ["start-iat.py"],
    zip_safe=True,
    packages=find_packages(),
    keywords = [     ],
    classifiers = [
    'Development Status :: 3 - Alpha',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Topic :: Software Development :: Libraries :: Python Modules',
    ],
    test_suite = 'nose.collector',
    entry_points="""
    [paste.paster_create_template]
    bourbon = bourbon.templates:BourbonApp
    """
    )
    
