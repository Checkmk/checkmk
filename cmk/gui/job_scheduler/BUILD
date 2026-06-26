load("@aspect_rules_py//py:defs.bzl", "py_library")
load("@cmk_requirements//:requirements.bzl", "requirement")

py_library(
    name = "job_scheduler",
    srcs = glob(["**/*.py"]),
    imports = ["../../.."],
    visibility = [
        "//bin:__pkg__",
        "//cmk:__subpackages__",
        "//tests:__subpackages__",
    ],
    deps = [
        "//cmk/gui:app",
        "//cmk/gui:config",
        "//cmk/gui:core_toolkit",
        "//cmk/gui:session_context",
        "//cmk/gui/background_job/job",
        "//cmk/utils:paths",
        "//packages/cmk-ccc:daemon",
        "//packages/cmk-ccc:exceptions",
        "//packages/cmk-ccc:log",
        "//packages/cmk-ccc:site",
        "//packages/cmk-ccc:store",
        "//packages/cmk-ccc:version",
        "//packages/cmk-ccc:version-info",
        "//packages/cmk-crash:crash",
        "//packages/cmk-trace",
        "//packages/cmk-wsgi",
        requirement("fastapi"),
        requirement("opentelemetry-instrumentation-fastapi"),
        requirement("setproctitle"),
        requirement("uvicorn"),
    ],
)
