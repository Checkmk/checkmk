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
    name = "logwatch",
    srcs = ["__test__.py"] + glob(["**/*.py"]),
    args = ["tests/unit/cmk/gui/logwatch"],
    main = ":__test__.py",
    deps = [
        ":__test__",
        "//cmk/gui/logwatch",
        "//packages/cmk-ccc:hostaddress",
        requirement("pytest"),
    ],
)
