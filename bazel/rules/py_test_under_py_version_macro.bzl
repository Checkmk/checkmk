load("@aspect_rules_py//py:defs.bzl", "py_pytest_main", "py_test")

def _py_test_under_py_version_impl(name, visibility, deps, srcs, data, python_version):
    py_pytest_main(
        name = name + "__test__",
        deps = deps,
        visibility = visibility,
    )

    py_test(
        name = name,
        srcs = [
            name + "__test__.py",
        ] + srcs,
        python_version = python_version,
        main = ":%s__test__.py" % name,
        data = data,
        deps = [
            ":%s__test__" % name,
        ] + deps,
        visibility = visibility,
    )

py_test_under_py_version = macro(
    attrs = {
        "srcs": attr.label_list(mandatory = True),
        "data": attr.label_list(),
        "deps": attr.label_list(),
        "python_version": attr.string(mandatory = True),
    },
    implementation = _py_test_under_py_version_impl,
)
