load("@aspect_rules_py//py:defs.bzl", "py_library")
load("@bazel_skylib//rules:build_test.bzl", "build_test")
load("@cmk_requirements//:requirements.bzl", "requirement")
load("@rules_python//python:packaging.bzl", "py_wheel")
load("//bazel/rules:doctest.bzl", "py_doc_test")
load("//bazel/rules:package_wheel.bzl", "package_wheel")
load("//bazel/rules:py_requirements_test.bzl", "py_requirements_test")

exports_files([
    "pyproject.toml",
    "requirements.in",
])

py_library(
    name = "cmk-wsgi",
    srcs = glob(
        include = ["cmk/gui/wsgi/**/*.py"],
    ) + ["cmk/gui/wsgi/applications/index.wsgi"],
    imports = ["."],
    visibility = [
        "//bin:__pkg__",
        "//cmk:__subpackages__",
        "//non-free/packages/cmk-agent-registration-extended:__pkg__",
        "//omd/packages/check_mk:__pkg__",
        "//tests:__subpackages__",
    ],
    deps = [
        "//cmk/gui:auth",
        "//cmk/gui:config",
        "//cmk/gui:core_toolkit",
        "//cmk/gui:html_toolkit",
        "//cmk/gui:page_toolkit",
        "//cmk/gui:request_globals",
        "//cmk/gui/dashboard:page_token_error",
        "//cmk/gui/openapi:utils",
        "//cmk/gui/openapi:versioned_endpoint_map",
        "//cmk/gui/openapi/framework",
        "//cmk/gui/openapi/framework:api_config",
        "//cmk/gui/openapi/framework:core",
        "//cmk/gui/openapi/framework:types",
        "//cmk/gui/openapi/restful_objects",
        "//cmk/gui/openapi/restful_objects:type_defs",
        "//cmk/gui/openapi/spec:utils",
        "//cmk/gui/token_auth",
        "//cmk/gui/userdb",
        "//cmk/gui/utils:middle",
        "//cmk/gui/watolib",
        "//cmk/gui/watolib:config_infra",
        "//cmk/utils:paths",
        "//packages/cmk-ccc:exceptions",
        "//packages/cmk-ccc:site",
        "//packages/cmk-ccc:store",
        "//packages/cmk-ccc:version",
        "//packages/cmk-ccc:version-info",
        "//packages/cmk-crypto",
        "//packages/cmk-livestatus-client",
        "//packages/cmk-profiling:gui",
        "//packages/cmk-trace",
        "//packages/cmk-web",
        requirement("apispec"),
        requirement("flask"),
        requirement("opentelemetry-api"),
        requirement("opentelemetry-instrumentation-redis"),
        requirement("opentelemetry-instrumentation-requests"),
        requirement("opentelemetry-instrumentation-wsgi"),
        requirement("pyprof2calltree"),
        requirement("pyyaml"),
        requirement("werkzeug"),
    ],
)

py_doc_test(
    name = "doctest",
    size = "small",
    srcs = [":cmk-wsgi"],
)

py_wheel(
    name = "wheel",
    distribution = "cmk-wsgi",
    strip_path_prefixes = ["packages/cmk-wsgi"],
    # TODO: Duplicated from pyproject.toml
    version = "1.0.0",
    visibility = ["//visibility:public"],
    deps = [
        ":cmk-wsgi",
    ],
)

build_test(
    name = "build_test",
    targets = [
        ":wheel",
    ],
)

package_wheel(
    name = "pkg_tar",
    visibility = ["//visibility:public"],
    whl = "wheel",
)

sh_library(
    name = "f12",
    srcs = [
        "cmk/gui/wsgi/.f12",
    ],
)

py_requirements_test(
    name = "requirements-test",
    known_unused = ["pyyaml"],  # needed transitively by apispec.yaml_utils;
    libs = [
        ":cmk-wsgi",
    ],
    requirements_in = "requirements.in",
)
