bibs
====
Bibliographic Search
------------

A python module with the goal of a shared syntax for querying public Bibliographic APIs and a simple and flexible extension model.

(in development)

Example
-----

	from bibs.bibs import Bibs

	b = Bibs()
	results = b.search("title->Tom Sawyer", 'dplav1', 'items')

where **title->Tom Sawyer** is the *query*, **dplav1** is the bibliographic *source*, and **items** is the *api*.


Query
-----

Queries are composed of one or more key/value pairs. Keys and their values are to be separated by an **->**, while each pair is separated by an **:**. Key/values may also be nested. For instance, to search Open Library's "query" api for all editions that contain a Title of Contents with an entry for page 19:

	b.search("types->edition:table_of_contents->pagenum->19", 'openlibrary', 'query') 

Multiple values may be indicated by an **|** separating the values, like:

	 b.search('types->edition:subjects->war|peace', 'openlibrary', 'query')

Or,

	 b.search('oclc->424023|isbn->0030110408', 'hathitrust', 'multi_volumes_full')


Optional arguments are to be preceded by an **@**, like:

	 b.search('types->edition:title->Macbeth @publish_date->null:limit->5', 'openlibrary', 'query')

where **publish_date->null** will request data from the **publish_date** field for all editions found whose title is 'Macbeth', and **limit->5** will limit the results to five.  


Source
-----

Each source is modeled in YAML, providing the information necessary to parse queries and the documentation on how to form queries. 


Currently supported Sources:

- dplav2           (<a href='http://dp.la'>Digital Public Library of America</a>)
- bhlv2            (<a href='http://biodiversityheritagelibrary.org'>Biodiversity Heritage Library</a>)
- hathitrust       (<a href='http://hathitrust.org'>Hathi Trust</a>)
- openlibrary      (<a href='http://openlibrary.org'>Open Library</a>)
- europeanav2      (<a href='http://europeana.eu'>Europeana</a>)
- googlebooks      (<a href='http://books.google.com'>Google Books</a>)
- locsruv1.1       (<a href='http://loc.gov/standards/sru'>Library of Congress SRU</a>)
- librarythingv1.1 (<a href='http://www.librarything.com'>Library Thing</a>)
- dlesev1.1        (<a href='http://www.dlese.org'>Digital Library for Earth System Education</a>)



Installation
-----

- Download and unpack the zip.
- "pip install bibs/ -r bibs/requirements.txt" or run "python bibs/setup.py install" and install the dependencies yourself.

Dependencies
- lxml
- PyYAML
- xmltodict
- dict2xml