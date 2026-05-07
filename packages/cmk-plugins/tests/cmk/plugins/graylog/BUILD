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
    name = "graylog-test",
    size = "small",
    srcs = glob(["**/*.py"]) + [":__test__.py"],
    data = glob(["**/*.yaml"]),
    main = ":__test__.py",
    deps = [
        ":__test__",
        "//packages/cmk-plugins/cmk/plugins/graylog",
        requirement("pytest"),
        requirement("time-machine"),
        requirement("vcrpy"),
    ],
)
