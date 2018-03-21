
#!/usr/bin/python
# call using
# > py.test -s -k test_html_generator.py

# internal imports
from classes import RequestHandlerTester


# TODO: Write valid test
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


# TODO: Write valid test
def test_cookie_handling():

    html = RequestHandlerTester()

    html.cookies = {"cookie1": {"key": "1a"}}
    assert html.get_cookie_names() == ["cookie1"]
    assert html.has_cookie("cookie1")
    assert not html.has_cookie("cookie2")
    #TODO: Write proper test assert html.cookie("cookie1", "2n class") == "1a"
    assert html.cookie("cookie2", "2n class") == "2n class"


# TODO: Write valid test
def test_request_timeout():

    html = RequestHandlerTester()

    html.request_timeout()
    html.enable_request_timeout()
    html.disable_request_timeout()
    try:
        html.handle_request_timeout(3, 4)
    except:
        pass


# TODO: Write valid test
def test_request_processing():

    html = RequestHandlerTester()
    html.add_var("varname", "1a")
    html.add_var("varname2", 1)

    html.get_unicode_input("varname", deflt = "lol")
    html.get_integer_input("varname2")
    html.get_request(exclude_vars=["varname2"])
    # TODO: Make a test which works:
    # html.parse_field_storage(["field1", "field2"], handle_uploads_as_file_obj = False)


# TODO: Write valid test
def test_content_type():

    html = RequestHandlerTester()
    html.add_var("varname", "1a")

    #html.set_output_format("csv")
    #html.set_content_type("csv")
    #html.is_api_call()


# TODO: Write valid test
def test_transaction_ids():

    html = RequestHandlerTester()

    varname = "Variable"
    used_ids = ["1", "2"]
    used_id = "1"

    html.set_ignore_transids()
    html.fresh_transid()
    html.get_transid()
    html.store_new_transids()
    html.invalidate_transid(used_id)
    html.transaction_valid()
    html.is_transaction()
    html.check_transaction()

