load("@aspect_rules_py//py:defs.bzl", "py_pytest_main")
load("@cmk_requirements//:requirements.bzl", "requirement")
load("//bazel/rules:py_cmk_test.bzl", "py_cmk_test")

py_pytest_main(
    name = "__test__",
    deps = [
        requirement("coverage"),
        requirement("pytest"),
    ],
)

py_cmk_test(
    name = "fields",
    srcs = ["__test__.py"] + glob(["**/*.py"]),
    args = ["tests/unit/cmk/gui/fields"],
    main = ":__test__.py",
    use_project_pytest_config = True,
    deps = [
        ":__test__",
        "//cmk/gui/fields",
        "//cmk/gui/fields:base",
        requirement("marshmallow"),
        requirement("pytest"),
    ],
)
