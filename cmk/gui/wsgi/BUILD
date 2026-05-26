load("@aspect_rules_py//py:defs.bzl", "py_library")
load("@cmk_requirements//:requirements.bzl", "requirement")

exports_files([".f12"])

py_library(
    name = "utils",
    srcs = ["utils.py"],
    imports = ["../../.."],
    visibility = [
        "//cmk:__subpackages__",
        "//tests:__subpackages__",
    ],
    deps = [
        requirement("flask"),
    ],
)

py_library(
    name = "wsgi",
    srcs = glob(
        include = ["**/*.py"],
        exclude = ["utils.py"],
    ) + ["applications/index.wsgi"],
    imports = ["../../.."],
    visibility = [
        "//cmk:__subpackages__",
        "//tests:__subpackages__",
    ],
    deps = [
        ":utils",
        "//cmk/gui:auth",
        "//cmk/gui:config",
        "//cmk/gui:core_toolkit",
        "//cmk/gui:html_toolkit",
        "//cmk/gui:page_toolkit",
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
        "//cmk/gui/utils:cookies",
        "//cmk/gui/utils:escaping",
        "//cmk/gui/utils:html",
        "//cmk/gui/utils:mobile",
        "//cmk/gui/utils:output_funnel",
        "//cmk/gui/utils:roles",
        "//cmk/gui/utils:timeout_manager",
        "//cmk/gui/utils:urls",
        "//cmk/gui/utils:user_errors",
        "//cmk/utils:paths",
        "//packages/cmk-ccc:exceptions",
        "//packages/cmk-ccc:site",
        "//packages/cmk-ccc:store",
        "//packages/cmk-ccc:version",
        "//packages/cmk-crypto",
        "//packages/cmk-livestatus-client",
        "//packages/cmk-trace",
        requirement("apispec"),
        requirement("flask"),
        requirement("opentelemetry-api"),
        requirement("opentelemetry-instrumentation-redis"),
        requirement("opentelemetry-instrumentation-requests"),
        requirement("opentelemetry-instrumentation-wsgi"),
        requirement("pyprof2calltree"),
        requirement("werkzeug"),
    ],
)
