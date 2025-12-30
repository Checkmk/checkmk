load("@aspect_rules_py//py:defs.bzl", "py_pytest_main", "py_test")

def py_tests_for_python_versions(
        name,
        python_versions,
        requirements,
        srcs,
        data = [],
        deps = [],
        visibility = None):
    """Run tests for multiple python versions.

    Args:
      name: Name of the target (a `test_suite`).
      python_versions: List of strings, versions to be tested.
      requirements: Requirements for the tests, per python version.
      srcs: Source code for the test cases.
      data: Optional, data added to the test cases.
      deps: Optional, dependencies for the test cases.
      visibility: Optional, the visibility of the target.

    """
    tests = []

    for v in python_versions:
        test_name = "py-" + v

        py_pytest_main(
            name = test_name + "__test__",
            tags = ["manual"],
            visibility = ["//visibility:private"],
        )

        py_test(
            name = test_name,
            srcs = [test_name + "__test__.py"] + srcs,
            tags = ["manual"],
            python_version = v,
            main = ":%s__test__.py" % test_name,
            data = data,
            deps = requirements[v] + [
                ":" + test_name + "__test__",
            ] + deps,
            visibility = ["//visibility:private"],
        )

        tests.append(":" + test_name)

    native.test_suite(
        name = name,
        tests = tests,
        visibility = visibility,
    )
