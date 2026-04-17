load("@aspect_rules_py//py:defs.bzl", "py_library")
load("@cmk_requirements//:requirements.bzl", "requirement")

py_library(
    name = "job_scheduler",
    srcs = glob(["**/*.py"]),
    imports = ["../../.."],
    visibility = [
        "//cmk:__subpackages__",
        "//tests:__subpackages__",
    ],
    deps = [
        "//cmk/gui",
        "//cmk/gui:config",
        "//cmk/gui:cron",
        "//cmk/gui:log",
        "//cmk/gui:session",
        "//cmk/gui:single_global_setting",
        "//cmk/gui/background_job/job",
        "//cmk/utils",
        "//packages/cmk-ccc:crash-reporting",
        "//packages/cmk-ccc:daemon",
        "//packages/cmk-ccc:exceptions",
        "//packages/cmk-ccc:site",
        "//packages/cmk-ccc:store",
        "//packages/cmk-ccc:version",
        "//packages/cmk-trace",
        requirement("fastapi"),
        requirement("opentelemetry-instrumentation-fastapi"),
        requirement("setproctitle"),
        requirement("uvicorn"),
    ],
)
