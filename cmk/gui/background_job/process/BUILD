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
        "//cmk/gui:i18n",
        "//cmk/gui:log",
        "//cmk/gui:single_global_setting",
        "//cmk/gui/background_job/job",
        # session.py is still in the monolithic gui target. No cycle since
        # nothing in the monolithic gui imports from this process/ package
        # (it is invoked at runtime via importlib.import_module).
        "//cmk/gui",
        "//cmk/utils",
        "//packages/cmk-ccc:exceptions",
        "//packages/cmk-ccc:store",
        "//packages/cmk-ccc:user",
        "//packages/cmk-ccc:version",
        "//packages/cmk-trace",
        requirement("setproctitle"),
    ],
)
