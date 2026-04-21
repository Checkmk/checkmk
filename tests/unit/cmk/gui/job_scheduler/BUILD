load("@aspect_rules_py//py:defs.bzl", "py_test")
load("@cmk_requirements//:requirements.bzl", "requirement")

py_test(
    name = "job_scheduler",
    srcs = glob(["**/*.py"]),
    args = ["tests/unit/cmk/gui/job_scheduler"],
    env = {"EDITION": "community"},
    pytest_main = True,
    deps = [
        "//cmk/gui:config",
        "//cmk/gui:cron",
        "//cmk/gui:job_scheduler_client",
        "//cmk/gui/background_job/job",
        "//cmk/gui/job_scheduler",
        "//tests/unit:conftest",
        "//tests/unit/cmk/gui:conftest",
        requirement("fastapi"),
        requirement("httpx"),
        requirement("pytest"),
        requirement("time-machine"),
    ],
)
