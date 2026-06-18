load("@aspect_rules_py//py:defs.bzl", "py_library")
load("@cmk_requirements//:requirements.bzl", "requirement")

py_library(
    name = "automation-helper",
    srcs = glob(["**/*.py"]),
    imports = ["../../.."],
    visibility = [
        "//cmk:__pkg__",
        "//cmk/base:__subpackages__",
    ],
    deps = [
        "//cmk/automations",
        "//cmk/base:app",
        "//cmk/base:config",
        "//cmk/base/automations",
        "//cmk/utils",
        "//cmk/utils:redis",
        "//packages/cmk-ccc:daemon",
        "//packages/cmk-ccc:site",
        "//packages/cmk-ccc:tty",
        "//packages/cmk-ccc:version",
        "//packages/cmk-check-engine/cmk/checkengine/plugins",
        "//packages/cmk-trace",
        requirement("fastapi"),
        requirement("opentelemetry-api"),
        requirement("opentelemetry-sdk"),
        requirement("opentelemetry-instrumentation-fastapi"),
        requirement("pydantic"),
        requirement("redis"),
        requirement("setproctitle"),
        requirement("uvicorn"),
        requirement("watchdog"),
    ],
)
