

You have created a new function for the html class or you want to update its behaviour to the new state.

1. Create a file in this folder "$testname.testgen"

2. This file is a dictionary with the following fields: "name", "arguments", "attributes" and "variables.
   An example can be found in the file "help.testgen". All dict values need to be a list with all values to test.

3. In web/generate_integration.py, create a function
   (Replace the "new" argument by "old" if the test shall reflect the old state given in class_deprecated_renderer.py)

    def test_$testname():
        html_tests.load_gentest_file("$testname", "new")

4. run the test generation script using pytest

        pytest -sv -m html_gentest web/generate_integration.py -k test_$testname

5. View the generated test file in order to make sure all tests correspond to the wanted behaviour

6. Run the test using

        pytest -sv -k test_$testname
