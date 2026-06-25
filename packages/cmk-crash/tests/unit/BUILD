load("@aspect_rules_py//py:defs.bzl", "py_pytest_main")
load("@cmk_requirements//:requirements.bzl", "requirement")
load("//bazel/rules:py_cmk_test.bzl", "py_cmk_test")

py_pytest_main(
    name = "__test__",
    deps = [
        requirement("pytest"),
    ],
)

py_cmk_test(
    name = "unit",
    size = "small",
    srcs = glob(["**/*.py"]) + [":__test__.py"],
    main = "__test__.py",
    deps = [
        ":__test__",
        "//packages/cmk-crash:crash",
        "//packages/cmk-crash:crash_reporting",
        requirement("pytest"),
    ],
)
