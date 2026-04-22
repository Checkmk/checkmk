load("@aspect_rules_py//py:defs.bzl", "py_library", "py_pytest_main", "py_test")
load("@cmk_requirements//:requirements.bzl", "requirement")

py_library(
    name = "conftest",
    testonly = True,
    srcs = [
        "__init__.py",
        "conftest.py",
    ],
    visibility = ["//tests/unit/cmk/gui/openapi:__subpackages__"],
    deps = [
        "//cmk/automations",
        "//cmk/gui:script_helpers",
        "//cmk/gui:session",
        "//cmk/gui/mkeventd",
        "//cmk/gui/watolib",
        "//cmk/gui/wsgi",
        "//packages/cmk-ccc:hostaddress",
        "//tests:rest_api_client",
        "//tests/testlib/gui",
        requirement("pytest"),
    ],
)

py_pytest_main(
    name = "__test__",
    deps = [
        requirement("pytest"),
        requirement("pytest-xdist"),
    ],
)

# Catch-all py_test covering openapi files and subdirs that don't have their own BUILD.
py_test(
    name = "openapi",
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
        "//cmk:validate_config",
        "//cmk/gui",
        "//cmk/gui/openapi/spec/spec_generator",
        "//cmk/gui/openapi/spec/spec_generator:_core",
        "//tests/unit:conftest",
        "//tests/unit/cmk/gui:conftest",
        "//tests/unit/cmk/gui:init_py",
        requirement("apispec-oneofschema"),
        requirement("fakeredis"),
        requirement("fastapi"),
        requirement("flask"),
        requirement("httpx"),
        requirement("marshmallow"),
        requirement("marshmallow-oneofschema"),
        requirement("openapi-spec-validator"),
        requirement("polyfactory"),
        requirement("pytest"),
        requirement("pytest-asyncio"),
        requirement("pytest-mock"),
        requirement("pytest-random-order"),
        requirement("python-dateutil"),
        requirement("pyyaml"),
        requirement("responses"),
        requirement("time-machine"),
        requirement("werkzeug"),
    ],
)
