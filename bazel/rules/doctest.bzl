# Adapted from https://github.com/1e100/bazel_doctest/tree/master
"""Implements Python doctest support for Bazel."""

load("@rules_python//python:defs.bzl", "py_test")

DOCTEST_TPL = r"""
import doctest, unittest


def load_tests(loader, tests, ignore):
{}
    return tests


if __name__ == "__main__":
    unittest.main()
"""

# TODO: Make `ELLIPSIS` optional?
ADD_TESTS_TPL = r"    tests.addTests(doctest.DocTestSuite('{}', optionflags=doctest.ELLIPSIS))"

def _file_to_module(file):
    if file.basename == "__init__.py":
        path = file.dirname
    else:
        path = file.path[:-len(file.extension) - 1]
    return path.replace("/", ".")

def _impl(ctx):
    modules = []
    for src in ctx.attr.srcs:
        modules.extend([
            ADD_TESTS_TPL.format(_file_to_module(file))
            for file in src.files.to_list()
        ])
    runner = ctx.actions.declare_file(ctx.attr.name)
    content = DOCTEST_TPL.format("\n".join(modules))
    ctx.actions.write(
        runner,
        content = content,
    )
    return [
        DefaultInfo(files = depset([runner])),
    ]

_runner = rule(
    implementation = _impl,
    attrs = {
        "srcs": attr.label_list(
            mandatory = True,
            providers = [DefaultInfo],
            doc = "List of Python targets potentially containing doctests.",
        ),
    },
)

# Deliberately using the required _test convention
# so that this is easy to search for.
def py_doc_test(name, srcs, deps = [], **kwargs):
    runner_py = name + "-doctest-runner.py"
    _runner(
        name = runner_py,
        srcs = srcs,
        testonly = True,
    )
    py_test(
        name = name,
        srcs = [runner_py],
        deps = srcs + deps,
        main = runner_py,
        legacy_create_init = False,
        **kwargs
    )
