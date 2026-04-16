load("@aspect_rules_py//py:defs.bzl", "py_library", "py_pytest_main", "py_test")
load("@cmk_requirements//:requirements.bzl", "requirement")

py_library(
    name = "conftest",
    testonly = True,
    srcs = ["conftest.py"],
    visibility = ["//tests/unit/cmk/gui:__subpackages__"],
    deps = [
        "//cmk/gui",
        "//cmk/gui/livestatus_utils",
        "//cmk/utils",
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
    name = "gui",
    srcs = ["__test__.py"] + glob(
        include = ["**/*.py"],
        exclude = ["conftest.py"],
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
    visibility = ["//visibility:private"],
    deps = [
        ":__test__",
        ":conftest",
        "//tests/unit:conftest",
        requirement("apispec-oneofschema"),
        requirement("beautifulsoup4"),
        requirement("fakeredis"),
        requirement("fastapi"),
        requirement("flask"),
        requirement("httpx"),
        requirement("marshmallow"),
        requirement("marshmallow-oneofschema"),
        requirement("openapi-spec-validator"),
        requirement("opentelemetry-sdk"),
        requirement("polyfactory"),
        requirement("pytest-mock"),
        requirement("pytest-asyncio"),
        requirement("pytest-random-order"),
        requirement("python-dateutil"),
        requirement("python-ldap"),
        requirement("pyyaml"),
        requirement("responses"),
        requirement("time-machine"),
        requirement("werkzeug"),
        "//cmk:validate_config",
        "//cmk/bi",
        "//cmk/gui",
        "//cmk/gui/job_scheduler",
        "//cmk/gui/openapi/spec/spec_generator",
        "//cmk/gui/openapi/spec/spec_generator:_core",
        "//cmk/gui/utils:html_tag_balance",
        "//omd/packages/omd:omdlib",
        "//tests/testlib/common:empty_config",
        "//tests/testlib/common:utils",
        "//tests/testlib/unit",
    ],
)
