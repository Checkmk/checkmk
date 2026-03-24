# directory: 'rules'

The directory is used to store (JSON) data structures corresponding to various 'rules'.
These data structures are injected into the base-site during the _update-test_ testsuite run,
at the _test setup_ stage using the REST-API `POST /domain-types/rule/collections/all`.

The data structures are _either_ following (legacy) Valuespecs _or_ following Formspecs.

# sub-directory: 'overrides_for_base_site_2.5.0'

If the data structures are supported in 2.4.0 but _not_ in 2.5.0,
then place the 2.5.0 supported data structure in this directory.

# Example

```
rules
|- fileinfo_groups.json  # consists of `Formspec` data structure supported by 2.4.0 sites only
|- overrides_for_base_site_2.5.0
    |- fileinfo_groups.json  # consists of `Valuespec` data structure supported by 2.5.0 sites only

```
