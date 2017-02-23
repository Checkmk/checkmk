#!/usr/bin/python
# call using
# > py.test -s -k test_html_generator.py

# external imports
import ast
import pprint
import itertools
import copy
import os
from os import listdir
from os.path import isfile, join

# internal imports
from testlib import cmk_path
from htmllib import HTML
from classes import HTMLOrigTester, Refactored_htmlTester
import tools


#######################################################################################
# HTML integration unit testing                                                       #
#                                                                                     #
# The following section defines a class for html integration unittesting.             #
# Some functions for building, saving and running these tests are provided.           #
# In the section below you can find functions to create cartesian products for        #
# arguments and the statespace.                                                       #
#                                                                                     #
# use OLD functionality for test: build_orig_test                                     #
# use NEW functionality for test: build_cmk_test                                      #
#                                                                                     #
# Create a new set of unittests:                                                      #
#   test = build_orig_test(function_name, arguments, state_in=None, add_vars=None)    #
#   assert save_html_test(function_name, test)                                        #
#                                                                                     #
# Run a set of unittests:                                                             #
#   test = load_html_test(function_name)                                              #
#   assert test.run()                                                                 #
#                                                                                     #
# For creating a set of tests have a look at the cartesian product section below.     #
#######################################################################################

class HtmlTest(object):


    # empty constructor
    def __init__(self):
        super(HtmlTest, self).__init__()
        self.function_name  = ''    # the function to be called
        self.arguments      = {}    # the arguments for the function call
        self.state_in       = {}    # the state of the html object before the function call
        self.add_vars       = {}    # the variables of the html object before the function call
        self.expected_html  = ''    # the expected generated html
        self.state_out      = {}    # the state of the html object after the function call
        self.return_value   = None  # the return value of the function call


    def __str__(self):
        return pprint.pformat(self.to_dict())


    # this is the standard constructor. This was necessary in order to make a constructor call from_dict
    def create(self, function_name, expected_html, arguments=None, state_in=None, add_vars=None, state_out=None, return_value=None):
        self.function_name  = function_name
        self.arguments      = copy.deepcopy(arguments) if arguments is not None else {}
        self.state_in       = copy.deepcopy(state_in)  if state_in is not None else {}
        self.add_vars       = copy.deepcopy(add_vars)  if add_vars is not None else {}
        self.expected_html  = expected_html
        self.state_out      = copy.deepcopy(state_out) if state_out is not None else {}
        self.return_value   = return_value
        return self


    # convert to dictionary
    def to_dict(self):
        # required attributes
        d = { "function_name": self.function_name, \
              "input"        : { "arguments"  : self.arguments, }, \
              "output"       : { "html_code"  : self.expected_html } }
        # optional attributes
        if self.state_in:
            d["input"]["attributes"] = self.state_in
        if self.add_vars:
            d["input"]["variables"] = self.add_vars
        if self.state_out:
            d["output"]["attributes"] = self.state_out
        if self.return_value is not None:
            d["output"]["return_value"] = self.return_value
        return d


    # parse a dictionary
    def from_dict(self, test):
        # required attributes
        self.function_name = test["function_name"]
        self.arguments     = test["input"]["arguments"]
        self.expected_html = test["output"]["html_code"]
        # optional attributes
        self.state_in      = test["input"].get("attributes", {})
        self.add_vars      = test["input"].get("variables", {})
        self.state_out     = test["output"].get("attributes", {})
        self.return_value  = test["output"].get("return_value", None)
        return self


    # validate that the test is meaningfull
    # TODO: DEPRECATED
    def validate(self):
        return True


    def run(self, html=None):
        global eval_func, set_html_state
        construct_html = (html is None)
        if construct_html:
            html = Refactored_htmlTester()
        add_html_vars(html, self.add_vars)
        set_html_state(html, self.state_in)
        return_value, html_code = eval_func(html, self.function_name, self.arguments)

        try:
            assert tools.compare_html(self.return_value, return_value)
        except Exception, e:
            print tools.bcolors.WARNING + "Test failed: the return value differs!\n%s" % self
            print tools.bcolors.WARNING + "EXPECTED: \n%s" % self.return_value
            print tools.bcolors.WARNING + "RETURNED: \n%s" % return_value
            raise e

        try:
            assert tools.compare_html(self.expected_html, html_code)
        except Exception, e:
            print tools.bcolors.WARNING + "Test failed: generated html code differs!\n%s" % self
            print tools.bcolors.WARNING + "EXPECTED: \n%s" % self.expected_html
            print tools.bcolors.WARNING + "GENERATED: \n%s" % html_code
            raise e

        try:
            assert tools.compare_attributes(tools.get_attributes(html), self.state_out)
        except Exception, e:
            print tools.bcolors.WARNING + "Test failed: output attributes differ!\n%s" % self
            print tools.bcolors.WARNING + "EXPECTED: \n%s" % pprint.pformat(self.state_out)
            print tools.bcolors.WARNING + "ATTRIBUTES: \n%s" % pprint.pformat({key: val for key, val in tools.get_attributes(html).iteritems() if key in self.state_out})
            raise e

        if construct_html:
            del html
        return True


# add variables to an html object
def add_html_vars(html, add_vars):
    if add_vars is None:
        return
    for key, value in add_vars.iteritems():
        if value is not None:
            html.add_var(key, value)


# set the state of an html object
def set_html_state(html, state):
    if state is None:
        return
    for key, value in state.iteritems():
        # get state and check if it is a list, then append
        val = getattr(html, key)
        if val is not None and isinstance(val, list):
            if isinstance(value, list):
                setattr(html, key, val + value)
            else:
                setattr(html, key, val + [value])
        else:
            setattr(html, key, value)


# run the memeber function for an html object with a number of arguments
def eval_func(html, function_name, arguments):
    html.plug()
    func = getattr(html, function_name)
    return_value = func(**arguments)
    html_code = html.drain()
    html.unplug()
    return return_value, html_code


# take a html object, set the state, add variables, run the function and create a test
def build_html_test(html, function_name, arguments, state_in=None, add_vars=None):
        add_html_vars(html, copy.deepcopy(add_vars))
        set_html_state(html, copy.deepcopy(state_in))
        orig_attrs    = copy.deepcopy(tools.get_attributes(html))
        return_value, expected_html = eval_func(html, function_name, copy.deepcopy(arguments))
        changed_attrs = {key: val for key, val in tools.get_attributes(html).iteritems()\
                                      if key not in orig_attrs or val != orig_attrs[key]}
        return HtmlTest().create(function_name,
                                 expected_html,
                                 arguments=arguments,
                                 state_in=state_in,
                                 add_vars=add_vars,
                                 state_out=changed_attrs,
                                 return_value=return_value)


# build a test using the HTMLOrigTester function
def build_orig_test(function_name, args, state_in=None, add_vars=None):
    orig = HTMLOrigTester()
    test = build_html_test(orig, function_name, args, state_in, add_vars)
    del orig
    return test


# build a test using the HTMLOrigTester function
def build_cmk_test(function_name, args, state_in=None, add_vars=None):
    cmk = Refactored_htmlTester()
    test = build_html_test(cmk, function_name, args, state_in, add_vars)
    del cmk
    return test


# write a list of html tests into a unittest file
def save_html_test(test_name, test, test_files_dir = "%s/tests/web/unittest_files" % cmk_path()):
    if not isinstance(test, list):
        test = [test]
    assert all(isinstance(t, HtmlTest) for t in test), test
    if not os.path.exists(test_files_dir):
        os.makedirs(test_files_dir)
    file_location = "%s/%s.unittest" % (test_files_dir.rstrip('/'), test_name)
    with open(file_location, "w+") as tfile:
        tfile.write(pprint.pformat([t.to_dict() for t in test]))
    return file_location


# load a unittest file and return a list of test objects
def load_html_test(test_name, test_files_dir = "%s/tests/web/unittest_files" % cmk_path()):
    try:
        with open("%s/%s.unittest" % (test_files_dir.rstrip('/'), test_name), "r") as tfile:
            tests = ast.literal_eval(tfile.read())
    except Exception, e:
        print tools.bcolors.WARNING + "\nERROR: No test file for test '%s'.\n" % test_name \
               + "Generate a test file first, e.g. by calling 'py.test -sv -m html_gentest -k test_generate_integration'.\n"
        raise e

    if not isinstance(tests, list):
        tests = [tests]
    try:
        tests = [HtmlTest().from_dict(test) for test in tests]
        assert all(test.validate() for test in tests)
        return tests
    except Exception, e:
        print tools.bcolors.WARNING + "WARNING! Unit test %s could not be validated." % test_name
        raise e
        return None



#######################################################################################
# Creating cartesion state and argument products for unittests                        #
#                                                                                     #
# The following functions can be used if many tests with different combinations of    #
# arguments or state variables need to be constructed.                                #
# They expect dicts where every value is a list. This list will then be used for the  #
# cartesian product.                                                                  #
#                                                                                     #
# A typical example to use these functions would be:                                  #
#   function_name = "header"                                                          #
#   arguments = {"title": ["Test1", "Test2"],                                         #
#                "javascripts": [['hallo_welt.js'], ['adios_mundo.js']],              #
#                "stylesheets": [['pages'], ['pages', 'teststylesheet']], }           #
#   state_in  = {"header_sent": [True, False]}                                        #
#   tests = [ build_cmk_test(function_name, args, s_in)                               #
#             for args in get_cartesian_product(arguments)                            #
#             for s_in in get_cartesian_product(state_in)]                            #
#                                                                                     #
#######################################################################################

# cartesian product of dictionary value sets
# expects a dictionary where all values are list of possible values
def get_cartesian_product(dictionary):
    # expects list of values
    assert all(isinstance(dictionary[key], list) for key in dictionary.keys())
    # convert to (key, value) tuples so that itertools.product can construct
    # the cartesian product of the dict
    to_tuples = [ [(key, val) for val in dictionary[key]] for key in dictionary.keys() ]
    # convert the tuples back to dictionaries
    return [ {arg: val for arg, val in config} for config in itertools.product(*to_tuples)]


# cartesian product of all possible state and argument spaces
def get_tests_args_state(function_name, arguments, state_in):
    tests = []
    for s_in in get_cartesian_product(state_in):
        for args in get_cartesian_product(state_in):
            tests.append(build_orig_test(function_name, arguments, s_in))
    return tests


# cartesian product of all possible argument spaces
def get_tests_args(function_name, arguments, state_in=None):
    tests = []
    for args in get_cartesian_product(state_in):
        tests.append(build_orig_test(function_name, arguments, state_in))
    return tests



#######################################################################################
# User interface for creating tests.                                                  #
#                                                                                     #
# Call using                                                                          #
#                                                                                     #
#       pytest -sv -m html_gentest web/generate_integration.py -k testgen             #
#                                                                                     #
#######################################################################################


# cmk_version in ["running", "old"]
def load_gentest_file(test_name, cmk_version = "running"):
    assert test_name, "Specify a test file using the '--testfile $name' option!"
    genpath = cmk_path() + "/tests/web/unittest_generation/"
    ending  = ".testgen"
    filename = "%s/%s.%s" % (genpath.rstrip('/'), test_name, ending.lstrip('.'))
    try:
        with open(filename, "r") as tfile:
            test = ast.literal_eval(tfile.read())
    except Exception, e:
        print tools.bcolors.WARNING + "\nERROR: No gentest file for test '%s'.\n" % test_name \
               + "Generate a test file first (see README for more details!)\n"
        raise e

    function_name  = test.get("function_name", test_name)
    arguments  = test.get("arguments", {})
    states_in  = test.get("attributes", {})
    add_vars   = test.get("variables", {})

    tests = []
    build_test = build_orig_test if cmk_version == "old" else build_cmk_test
    for args in get_cartesian_product(arguments):
        for s_in in get_cartesian_product(states_in):
            for vars in get_cartesian_product(add_vars):
                tests.append(build_test(function_name, args, s_in, vars))
    # save the tests to file and write out
    testfile = save_html_test(filename.split('/')[-1].split('.')[0], tests)


def run_all_generated_tests(file_ending = ".testgen"):
    genpath = cmk_path() + "/tests/web/unittest_generation/"
    onlyfiles = [f for f in listdir(genpath) if f.endswith(".testgen") and isfile(join(genpath, f))]
    for test_name in onlyfiles:
        tests = load_html_test(test_name.rstrip(file_ending), test_files_dir = "%s/tests/web/unittest_files" % cmk_path())
        for test in tests:
            test.run()


