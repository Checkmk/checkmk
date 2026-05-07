load("@aspect_rules_py//py:defs.bzl", "py_pytest_main", "py_test")
load("@cmk_requirements//:requirements.bzl", "requirement")

py_pytest_main(
    name = "__test__",
    deps = [
        requirement("coverage"),
        requirement("pytest"),
    ],
)

py_test(
    name = "job_scheduler",
    srcs = ["__test__.py"] + glob(["**/*.py"]),
    args = ["tests/unit/cmk/gui/job_scheduler"],
    env = {"EDITION": "community"},
    main = ":__test__.py",
    deps = [
        ":__test__",
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
