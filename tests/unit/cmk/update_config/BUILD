load("@aspect_rules_py//py:defs.bzl", "py_library", "py_pytest_main")
load("@cmk_requirements//:requirements.bzl", "requirement")
load("//bazel/rules:py_cmk_test.bzl", "py_cmk_test")

py_library(
    name = "conftest",
    testonly = True,
    srcs = ["conftest.py"],
    visibility = [":__subpackages__"],
    deps = [
        "//cmk/plugins",
        "//tests/testlib/unit",
        requirement("flask"),
        requirement("pytest"),
        requirement("pytest-mock"),
    ],
)

py_pytest_main(
    name = "__test__",
    deps = [
        requirement("coverage"),
        requirement("pytest"),
    ],
)

py_cmk_test(
    name = "update_config",
    srcs = ["__test__.py"] + glob(
        include = ["**/*.py"],
        exclude = ["**/conftest.py"],
    ),
    args = [
        "--random-order-bucket=global",
    ],
    env = {"EDITION": "community"},
    main = ":__test__.py",
    use_project_pytest_config = True,
    visibility = ["//visibility:private"],
    deps = [
        ":__test__",
        ":conftest",
        "//cmk/update_config",
        "//cmk/utils:werks",
        "//packages/cmk-backup:gui",
        "//packages/cmk-backup:utils",
        "//packages/cmk-ccc:store",
        "//tests/unit:conftest",
        requirement("flask"),
        requirement("pytest"),
        requirement("pytest-asyncio"),
        requirement("pytest-random-order"),
        requirement("pytest-mock"),
    ],
)
