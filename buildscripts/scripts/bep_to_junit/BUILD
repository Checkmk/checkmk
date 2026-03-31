load("@aspect_rules_py//py:defs.bzl", "py_binary")

py_binary(
    name = "bep_to_junit",
    srcs = [
        "__init__.py",
        "__main__.py",
        "_bep_types.py",
        "_helpers.py",
        "_parser.py",
        "_xml_builders.py",
    ],
    imports = [".."],
    main = "__main__.py",
)
