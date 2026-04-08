load("@aspect_rules_py//py:defs.bzl", "py_pytest_main", "py_test")
load("@cmk_requirements//:requirements.bzl", "requirement")

py_pytest_main(
    name = "__test__",
    deps = [requirement("pytest")],
)

py_test(
    name = "bazel-test",
    size = "small",
    srcs = glob(["**/*.py"]) + [":__test__.py"],
    main = ":__test__.py",
    deps = [
        ":__test__",
        "//packages/cmk-plugins/cmk/plugins/bazel",
        requirement("pytest"),
        requirement("time-machine"),
    ],
)
