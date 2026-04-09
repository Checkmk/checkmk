load("@aspect_rules_py//py:defs.bzl", "py_library")
load("@cmk_requirements//:requirements.bzl", "requirement")

py_library(
    name = "job",
    srcs = glob(["**/*.py"]),
    imports = ["../../../.."],
    visibility = [
        "//cmk:__subpackages__",
        "//tests:__subpackages__",
    ],
    deps = [
        "//cmk/gui:config",
        "//cmk/gui:http",
        "//cmk/gui:i18n",
        "//cmk/gui:job_scheduler_client",
        "//cmk/gui:log",
        "//cmk/gui:logged_in",
        "//cmk/gui/utils:roles",
        "//cmk/gui/utils:urls",
        "//cmk/utils",
        "//packages/cmk-ccc:exceptions",
        "//packages/cmk-ccc:plugin-registry",
        "//packages/cmk-ccc:regex",
        "//packages/cmk-ccc:resulttype",
        "//packages/cmk-ccc:store",
        "//packages/cmk-ccc:user",
        "//packages/cmk-trace",
        requirement("pydantic"),
    ],
)
