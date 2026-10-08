load("@aspect_rules_py//py:defs.bzl", "py_library")
load("@cmk_requirements//:requirements.bzl", "requirement")

py_library(
    name = "automations",
    srcs = [
        "client.py",
        "engine.py",
        "logging.py",
    ] + glob([
        "backends/*.py",
        "models/*.py",
        "models/**/*.py",
        "results/*.py",
    ]),
    imports = ["../.."],
    visibility = [
        "//cmk:__subpackages__",
        "//non-free/packages/cmk-bakery:__pkg__",
        "//non-free/packages/cmk-plugins-nonfree/cmk/plugins/notifications:__pkg__",
        "//tests:__subpackages__",
    ],
    deps = [
        "//cmk/utils",
        "//cmk/utils:unixsocket_http",
        "//packages/cmk-ccc:debug",
        "//packages/cmk-ccc:exceptions",
        "//packages/cmk-ccc:i18n",
        "//packages/cmk-ccc:log",
        "//packages/cmk-ccc:plugin-registry",
        "//packages/cmk-ccc:timeout",
        "//packages/cmk-ccc:version",
        "//packages/cmk-check-engine:helper-interface",
        "//packages/cmk-check-engine:lib",
        "//packages/cmk-check-engine:specs",
        "//packages/cmk-check-engine/cmk/checkengine/discovery",
        "//packages/cmk-check-engine/cmk/checkengine/plugins",
        "//packages/cmk-diagnostics:automation_types",
        "//packages/cmk-events",
        "//packages/cmk-plugin-apis:automations",
        "//packages/cmk-plugin-apis:discover_plugins",
        "//packages/cmk-plugin-apis:password_store",
        "//packages/cmk-trace",
        requirement("requests"),
    ],
)

# The automation helper: a server that keeps the automation engine loaded. It is
# a library of its own, so that the client side does not pull in its server stack.
py_library(
    name = "helper",
    srcs = glob(["helper/*.py"]),
    imports = ["../.."],
    visibility = [
        "//cmk/base/automation_helper:__pkg__",
        "//tests:__subpackages__",
    ],
    deps = [
        ":automations",
        "//packages/cmk-ccc:log",
        "//packages/cmk-ccc:site",
        "//packages/cmk-trace",
        requirement("fastapi"),
        requirement("opentelemetry-api"),
        requirement("opentelemetry-sdk"),
        requirement("opentelemetry-instrumentation-fastapi"),
        requirement("pydantic"),
        requirement("redis"),
        requirement("uvicorn"),
        requirement("watchdog"),
    ],
)
