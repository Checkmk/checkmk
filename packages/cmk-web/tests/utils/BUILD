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
    name = "unit",
    size = "small",
    srcs = ["__test__.py"] + glob(["*.py"]),
    main = ":__test__.py",
    deps = [
        ":__test__",
        "//packages/cmk-web/cmk/web/utils",
        requirement("pytest"),
    ],
)
