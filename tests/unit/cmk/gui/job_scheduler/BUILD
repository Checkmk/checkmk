load("@aspect_rules_py//py:defs.bzl", "py_pytest_main")
load("@cmk_requirements//:requirements.bzl", "requirement")
load("//bazel/rules:py_cmk_test.bzl", "py_cmk_test")

py_pytest_main(
    name = "__test__",
    deps = [
        requirement("coverage"),
        requirement("pytest"),
    ],
)

py_cmk_test(
    name = "job_scheduler",
    srcs = ["__test__.py"] + glob(["**/*.py"]),
    args = ["tests/unit/cmk/gui/job_scheduler"],
    env = {"EDITION": "community"},
    main = ":__test__.py",
    use_project_pytest_config = True,
    deps = [
        ":__test__",
        "//cmk/gui:config",
        "//cmk/gui:core_toolkit",
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
