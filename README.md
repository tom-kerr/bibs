bibs
====
Bibliographic Search
------------

A python module with the goal of a shared syntax for querying public Bibliographic APIs and a simple and flexible extension model.

(in development)

<h2>Example</h2>

	from bibs import Bibs

	b = Bibs()
	results = b.search("title->Tom Sawyer", 'dplav1', 'items')

where **title->Tom Sawyer** is the *query*, **dplav1** is the bibliographic *source*, and **search** is the *api*.


Query
-----

Queries are composed of one or more key/value pairs. Keys and their values are to be separated by an '->', while each pair is separated by an ':'. Key/values may also be nested. For instance, to search Open Library's "query" api for all editions that contain a Title of Contents with an entry for page 19:

	b.search("types->edition:table_of_contents->pagenum->19", 'openlibrary', 'query') 

Multiple values may be indicated by an '|' separating the values, like:

	 b.search('types->edition:subjects->war|peace', 'openlibrary', 'query')
Or,
	 b.search('oclc->424023|isbn->0030110408', 'hathitrust', 'multi_volumes_full')


Source
-----

Currently supported Sources:

- dplav1      (<a href='http://dp.la'>Digital Public Library of America</a>)
- blhv2       (<a href='http://biodiversityheritagelibrary.org'>Biodiversity Heritage Library</a>)
- hathitrust  (<a href='http://hathitrust.org'>Hathi Trust</a>)
- openlibrary (<a href='http://openlibrary.org'>Open Library</a>)
- europeana   (<a href='http://europeana.eu'>Europeana</a>)
- googlebooks (<a href='http://books.google.com'>Google Books</a>


Api
---
