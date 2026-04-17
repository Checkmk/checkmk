load("@aspect_rules_py//py:defs.bzl", "py_library")
load("@cmk_requirements//:requirements.bzl", "requirement")

py_library(
    name = "process",
    srcs = glob(["**/*.py"]),
    imports = ["../../../.."],
    visibility = [
        "//cmk:__subpackages__",
        "//tests:__subpackages__",
    ],
    deps = [
        "//cmk/gui:crash_handler",
        "//cmk/gui:features",
        "//cmk/gui:flask_app",
        "//cmk/gui:http",
        "//cmk/gui:i18n",
        "//cmk/gui:log",
        "//cmk/gui:session",
        "//cmk/gui:single_global_setting",
        "//cmk/gui/background_job/job",
        "//cmk/gui/utils:roles",
        "//cmk/utils",
        "//packages/cmk-ccc:exceptions",
        "//packages/cmk-ccc:store",
        "//packages/cmk-ccc:user",
        "//packages/cmk-ccc:version",
        "//packages/cmk-trace",
        requirement("setproctitle"),
    ],
)
