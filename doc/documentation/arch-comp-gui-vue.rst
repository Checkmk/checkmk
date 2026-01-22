=========
GUI - Vue
=========

Introduction and goals
======================

To allow for more flexibility in how we display our user interface, we are
moving forward in splitting our frontend rendering from our python backend. To
this end, we are introducing Vue. In the long run, we want to

* stop calling JavaScript functions from python code,
* stop defining html inside python,
* use the backend solely as a means to provide data to or process data from the
  frontend.

Architecture
============

We introduce the `cmk-frontend-vue` package which hosts all vue-related
functionality. Vue is a modular frontend framework where multiple Vue apps
can coexist in a single page. As we implement it, as soon as the backend
provides a div with the `cmk_vue_app` data attribute, it will be picked up by
Vue and serve as an entry point to a Vue app.

FormSpec Rendering
------------------

A big part of Checkmk is the rendering of forms. As we move away from
Valuespecs onto FormSpecs, we introduce a new way to render FormSpecs in Vue.

To be able to do this, we need a way to exchange data between the backend to the
frontend. On the backend, this is handled by `cmk.gui.form_specs`. Here, we are
defining a translation layer in the form of a `FormSpecVisitor` class. For each
FormSpec, we register a visitor which handles data parsing, translation into the
frontend schema, validation and serializing for disk storage in a single place.

If a new FormSpec is introduced, first the shared typing of the FormSpec schema
needs to be created, there is a dedicated package for this `cmk-shared-typing`,
though its location and name will change in the near future. Second, a new
visitor needs to be implemented and registered. Finally, A new Vue component
needs to be created and registered in the `cmk-frontend-vue` package under the
`cmk-form` module.

