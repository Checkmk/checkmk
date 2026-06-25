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
    name = "kube-test",
    size = "small",
    srcs = glob(["**/*.py"]) + [":__test__.py"],
    main = ":__test__.py",
    deps = [
        ":__test__",
        "//packages/cmk-plugins/cmk/plugins/kube",
        requirement("kubernetes"),
        requirement("polyfactory"),
        requirement("pytest"),
        requirement("pytest-mock"),
        requirement("requests"),
    ],
)
