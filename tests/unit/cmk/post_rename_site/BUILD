load("@aspect_rules_py//py:defs.bzl", "py_pytest_main")
load("@cmk_requirements//:requirements.bzl", "requirement")
load("//bazel/rules:py_cmk_test.bzl", "py_cmk_test")

py_library(
    name = "conftest",
    testonly = True,
    srcs = [
        "conftest.py",
    ],
    visibility = [":__subpackages__"],
    deps = [
        "//cmk/gui:config",
        "//cmk/gui:core_toolkit",
        "//cmk/plugins",
        "//packages/cmk-ccc:user",
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
    name = "post_rename_site",
    size = "small",
    timeout = "moderate",
    srcs = ["__test__.py"] + glob(
        include = ["**/*.py"],
        exclude = [
            "**/conftest.py",
        ],
    ),
    args = [
        "--random-order-bucket=global",
    ],
    env = {"EDITION": "community"},
    main = ":__test__.py",
    use_project_pytest_config = True,
    visibility = ["//tests:__subpackages__"],
    deps = [
        ":__test__",
        ":conftest",
        "//cmk/post_rename_site",
        "//cmk/post_rename_site/plugins",
        "//tests/unit:conftest",
        requirement("pytest"),
        requirement("pytest-asyncio"),
        requirement("pytest-mock"),
        requirement("werkzeug"),
        requirement("flask"),
        requirement("pytest-random-order"),
    ],
)
