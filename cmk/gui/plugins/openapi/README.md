Checkmk OpenAPI
===============

Implementer. THIS IS IMPORTANT! PLEASE READ!

When writing a new API endpoint please make sure to adhere to these standards:

 * All API endpoints return a dictionary-structure which follows the
  "Restful Objects" specification. This specification defines `domain types`
  and their representations as single-objects or collections. To always adhere
  to this standard, please refer to the helper functions in the
  `restful_objects.constructors` module.

 * All API endpoints need to have a doc-string for documentation purposes.
   Keep the first line short, as there is limited space in the documentation
   for the overview.

 * If you create a new module in `endpoints`, make sure to add a short
   doc-string on top for documentation purposes.

Overview
--------

The main entities of the REST API system are `User`, `Request`, `Response`, `Endpoint`, `Decorator`, `API WSGI App`, `Request Schema`, `Response Schema`, `Path Schema`, `Header Schema`, `Permission Object` and `Endpoint registry`.

A `Endpoint` needs to be decorated by `Decorator`.

`Decorator` uses the `Request Schema` to determine if the `Request` sent by `User` is correct.
