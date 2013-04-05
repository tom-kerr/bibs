bibs
====
Bibliographic Search

A python module with the goal of a shared syntax for querying public Bibliographic APIs and a simple and flexible extension model.

(in development)

Example:

from bibs import Bibs

b = Bibs()
         #query				#source       #api
b.search("OCLC:424023|ISBN:0030110408", 'hathitrust', 'multi_volumes_full')

b.search("OCLC:424023|ISBN:0030110408", 'openlibrary', 'multi_volumes_full')

b.search("title:Tom Sawyer", 'openlibrary', 'search')

b.search("title:Tom Sawyer", 'dplav1', 'items')

b.search("wskey:xxxxxxx:q:Tom Sawyer", 'europeanav2', 'search')