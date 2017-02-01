
#!/usr/bin/python
# call using
# > py.test -s -k test_html_generator.py

# internal imports
from classes import RequestHandlerTester


def test_request_processing():

    html = RequestHandlerTester()

    varname = "Variable"
    value = "value"
    prefix = "prefix"
    used_ids = ["1", "2"]
    deflt = "deflt"
    default = "default"

    html.var(varname, deflt = None)
    html.has_var(varname)
    html.has_var_prefix(prefix)
    html.var_utf8(varname, deflt = None)
    html.all_vars()
    html.all_varnames_with_prefix(prefix)
    html.list_var(varname)
    html.add_var(varname, value)
    html.set_var(varname, value)
    html.del_var(varname)
    html.del_all_vars(prefix = None)
    html.stash_vars()
    html.unstash_vars()
    html.uploaded_file(varname, default = None)


def test_transaction_ids():

    html = RequestHandlerTester()

    varname = "Variable"
    used_ids = ["1", "2"]
    used_id = "1"


    # TODO: Can this please be dropped?
    html.some_id()
    html.set_ignore_transids()
    html.fresh_transid()
    html.get_transid()
    html.store_new_transids()
    html.invalidate_transid(used_id)
    html.transaction_valid()
    html.is_transaction()
    html.check_transaction()

