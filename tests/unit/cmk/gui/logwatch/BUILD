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
    name = "logwatch",
    srcs = ["__test__.py"] + glob(["**/*.py"]),
    args = ["tests/unit/cmk/gui/logwatch"],
    main = ":__test__.py",
    use_project_pytest_config = True,
    deps = [
        ":__test__",
        "//cmk/gui/logwatch",
        "//packages/cmk-ccc:hostaddress",
        requirement("pytest"),
    ],
)
