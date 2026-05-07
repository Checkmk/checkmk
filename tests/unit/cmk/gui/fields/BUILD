load("@aspect_rules_py//py:defs.bzl", "py_pytest_main", "py_test")
load("@cmk_requirements//:requirements.bzl", "requirement")

py_pytest_main(
    name = "__test__",
    deps = [
        requirement("coverage"),
        requirement("pytest"),
    ],
)

py_test(
    name = "fields",
    srcs = ["__test__.py"] + glob(["**/*.py"]),
    args = ["tests/unit/cmk/gui/fields"],
    main = ":__test__.py",
    deps = [
        ":__test__",
        "//cmk/gui/fields",
        "//cmk/gui/fields:base",
        requirement("marshmallow"),
        requirement("pytest"),
    ],
)
