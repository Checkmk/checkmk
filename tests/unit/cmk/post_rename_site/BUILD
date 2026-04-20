load("@aspect_rules_py//py:defs.bzl", "py_pytest_main", "py_test")
load("@cmk_requirements//:requirements.bzl", "requirement")

py_library(
    name = "conftest",
    testonly = True,
    srcs = [
        "conftest.py",
    ],
    visibility = [":__subpackages__"],
    deps = [
        "//cmk/gui",
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
        requirement("pytest"),
        # pytest-xdist for `--numprocesses=NPROC`
        requirement("pytest-xdist"),
    ],
)

py_test(
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
        "--config-file=$(location @//:pyproject.toml)",
        "--import-mode=importlib",
        "--random-order-bucket=global",
        "--dist=loadfile",
        "--numprocesses=4",
    ],
    data = ["@//:pyproject.toml"],
    env = {"EDITION": "community"},
    main = ":__test__.py",
    visibility = ["//tests:__subpackages__"],
    deps = [
        ":__test__",
        ":conftest",
        "//cmk/post_rename_site",
        "//cmk/post_rename_site/plugins",
        "//tests/testlib/unit",
        "//tests/unit:conftest",
        requirement("pytest"),
        requirement("pytest-asyncio"),
        requirement("pytest-mock"),
        requirement("werkzeug"),
        requirement("flask"),
        requirement("pytest-random-order"),
    ],
)
