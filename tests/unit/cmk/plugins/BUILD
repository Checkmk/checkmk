load("@aspect_rules_py//py:defs.bzl", "py_pytest_main", "py_test")
load("@cmk_requirements//:requirements.bzl", "requirement")

py_pytest_main(
    name = "__test__",
    deps = [
        requirement("pytest"),
        # pytest-xdist for `--numprocesses=NPROC`
        requirement("pytest-xdist"),
    ],
)

py_test(
    name = "plugins",
    srcs = ["__test__.py"] + glob(["**/*.py"]),
    args = [
        "--config-file=$(location @//:pyproject.toml)",
        "--import-mode=importlib",
        "--random-order-bucket=global",
        "--dist=loadfile",
        "--numprocesses=4",
    ],
    data = ["@//:pyproject.toml"] + glob(
        include = [
            "**/_check_form_submit_response",
            "**/*.json",
            "**/*.yaml",
        ],
    ),
    env = {"EDITION": "community"},
    main = ":__test__.py",
    visibility = ["//visibility:private"],
    deps = [
        ":__test__",
        "//cmk/legacy_checks",
        "//cmk/plugins",
        "//tests/testlib/common:repo",
        "//tests/testlib/unit",
        requirement("exchangelib"),
        requirement("feedparser"),
        requirement("google-cloud-asset"),
        requirement("google-cloud-monitoring"),
        requirement("polyfactory"),
        requirement("pysmb"),
        requirement("pytest"),
        requirement("pytest-mock"),
        requirement("pytest-asyncio"),
        requirement("pytest-random-order"),
        requirement("python-snap7"),
        requirement("requests"),
        requirement("responses"),
        requirement("time-machine"),
        requirement("vcrpy"),
    ],
)

py_library(
    name = "gcp_testlib",
    srcs = ["gcp/testlib.py"],
    visibility = ["//tests:__subpackages__"],
    deps = [
        requirement("google-cloud-monitoring"),
        requirement("pytest"),
        "//cmk/plugins",
    ],
)
