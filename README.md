bibs
====
Bibliographic Search
------------

A python module with the goal of a shared syntax for querying public Bibliographic APIs and a simple and flexible extension model.

(in development)

<h2>Example</h2>

	from bibs import Bibs

	b = Bibs()
	results = b.search("title->Tom Sawyer", 'openlibrary', 'search')

where **title->Tom Sawyer** is the *query*, **openlibrary** is the bibliographic *source*, and **search** is the *api*.


Query
-----

Queries are composed of one or more key/value pairs. Keys and their values are to be separated by an '->', while each pair is separated by an ':'. Key/values may also be nested. For instance, to search Open Library's "query" api for all editions that contain a Title of Contents with an entry for page 19:

	b.search("types->edition:table_of_contents->pagenum->19", 'openlibrary', 'query') 


Source
-----




Api
---
