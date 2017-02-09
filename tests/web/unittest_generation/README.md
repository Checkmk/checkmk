

You have created a new function for the html class or you want to update its behaviour to the new state.

How can you do this? --> Follow these steps!

1. Create a file in this folder "$testname.testgen"

2. This file has to be formated as follows:

        name = "beispiel"
        arguments = { "id": "test0", "class": ["test", "css"], }
        states = { "header_sent": True, "vars": ["var1"]}

3. If ALL values of the dicts (arguments or states) are lists, then these lists will be multiplied out.
   E.g. in the following example, a test will be created for each value of states (4 in total)

        name = "beispiel"
        arguments = { "id": "test0", "class": ["test", "css"], }
        states = { "header_sent": [True, False], "vars": [[], ["var1"]]}

4. run the test generation script using pytest

        pytest -sv -m html_gentest web/generate_integration.py -k testgen

5. View the generated test file in order to make sure all tests correspond to the wanted behaviour

6. Run the test using

        pytest -sv -k test_generated
