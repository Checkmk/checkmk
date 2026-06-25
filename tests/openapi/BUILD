load("@aspect_rules_py//py:defs.bzl", "py_library")
load("@bazel_skylib//rules:write_file.bzl", "write_file")
load("@cmk_requirements//:requirements.bzl", "requirement")
load("//bazel/rules:py_cmk_test.bzl", "py_cmk_test")

package(default_visibility = [":__subpackages__"])

py_library(
    name = "conftest",
    testonly = True,
    srcs = [
        "__init__.py",
        "conftest.py",
    ],
    deps = [
        "//cmk/gui:auth_core",
        "//cmk/gui:config",
        "//cmk/gui:core_toolkit",
        "//cmk/gui/utils:roles",
        "//cmk/gui/watolib:password_store",
        "//cmk/plugins",
        "//packages/cmk-ccc:user",
        "//packages/cmk-ccc:version",
        "//packages/cmk-livestatus-client:py_livestatus",
        "//tests/testlib:fake_site",
        "//tests/testlib:rest_api_client",
        "//tests/testlib/common:repo",
        "//tests/testlib/gui",
        requirement("flask"),
        requirement("pytest"),
        requirement("pytest-mock"),
    ],
)

write_file(
    name = "cannot_fail",
    out = "test_cannot_fail.py",
    content = [
        "def test_cannot_fail() -> None:",
        "    assert True",
    ],
)

py_cmk_test(
    name = "smoke",
    size = "small",
    srcs = [
        "test_cannot_fail.py",
    ],
    env = {"EDITION": "community"},
    use_project_pytest_config = True,
    deps = [
        ":conftest",
    ],
)

py_cmk_test(
    name = "repo_community",
    size = "small",
    timeout = "moderate",
    srcs = [
        "__init__.py",
    ] + glob(include = ["test_*.py"]),
    args = [
        "--random-order-bucket=global",
    ],
    env = {"EDITION": "community"},
    use_project_pytest_config = True,
    deps = [
        ":conftest",
        "//cmk:validate_config",
        "//cmk/gui:auth_core",
        "//cmk/gui:core_toolkit",
        "//cmk/gui:general_pages",
        "//cmk/gui:html_toolkit",
        "//cmk/gui/background_job/process",
        "//cmk/gui/fields",
        "//cmk/gui/form_specs",
        "//cmk/gui/graphing",
        "//cmk/gui/oauth2_connections",
        "//cmk/gui/openapi/api_endpoints",
        "//cmk/gui/openapi/endpoints",
        "//cmk/gui/openapi/framework",
        "//cmk/gui/plugins/wato/check_parameters:stub",
        "//cmk/gui/quick_setup",
        "//cmk/gui/rest_api_types:notifications",
        "//cmk/gui/sidebar",
        "//cmk/gui/userdb",
        "//cmk/gui/valuespec",
        "//cmk/gui/watolib",
        requirement("marshmallow-oneofschema"),
        requirement("polyfactory"),
        requirement("pytest-mock"),
        requirement("pytest-random-order"),
        requirement("time-machine"),
    ],
)
