load("@aspect_rules_py//py:defs.bzl", "py_library", "py_pytest_main", "py_test")
load("@cmk_requirements//:requirements.bzl", "requirement")

py_library(
    name = "conftest",
    testonly = True,
    srcs = ["conftest.py"],
    visibility = ["//tests/unit/cmk/gui:__subpackages__"],
    deps = [
        "//cmk/gui:config",
        "//cmk/gui:http",
        "//cmk/gui:login",
        "//cmk/gui:permissions",
        "//cmk/gui/livestatus_utils",
        "//cmk/gui/utils:roles",
        "//cmk/gui/watolib",
        "//cmk/gui/watolib:password_store",
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

py_library(
    name = "compare_html",
    testonly = True,
    srcs = ["compare_html.py"],
    visibility = ["//tests/unit/cmk/gui:__subpackages__"],
    deps = [
        "//cmk/gui/utils:html",
        requirement("beautifulsoup4"),
    ],
)

py_test(
    name = "availability_tests",
    srcs = glob(["test_availability_*.py"]),
    args = ["tests/unit/cmk/gui"],
    env = {"EDITION": "community"},
    pytest_main = True,
    deps = [
        ":conftest",
        "//cmk/gui/availability",
        "//cmk/utils",
        "//packages/cmk-ccc:hostaddress",
        "//packages/cmk-ccc:site",
        "//tests/unit:conftest",
        requirement("fido2"),
        requirement("marshmallow"),
        requirement("opentelemetry-sdk"),
        requirement("pytest"),
        requirement("python-ldap"),
        requirement("time-machine"),
    ],
)

py_test(
    name = "gui",
    srcs = ["__test__.py"] + glob(
        include = ["**/*.py"],
        exclude = [
            "compare_html.py",
            "conftest.py",
            "test_availability_*.py",
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
    visibility = ["//visibility:private"],
    deps = [
        ":__test__",
        ":compare_html",
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
        "//omd/packages/omd:omdlib",
        "//tests/testlib/common:empty_config",
        "//tests/testlib/common:utils",
        "//tests/testlib/unit",
    ],
)
