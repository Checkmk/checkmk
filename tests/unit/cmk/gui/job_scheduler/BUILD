load("@cmk_requirements//:requirements.bzl", "requirement")
load("//bazel/rules:py_cmk_test.bzl", "py_cmk_test")

py_cmk_test(
    name = "job_scheduler",
    srcs = glob(["**/*.py"]),
    args = ["tests/unit/cmk/gui/job_scheduler"],
    env = {"EDITION": "community"},
    use_project_pytest_config = True,
    deps = [
        "//cmk/gui:config",
        "//cmk/gui:core_toolkit",
        "//cmk/gui/background_job/job",
        "//cmk/gui/job_scheduler",
        "//tests/unit:conftest",
        "//tests/unit/cmk/gui:conftest",
        requirement("fastapi"),
        requirement("httpx"),
        requirement("time-machine"),
    ],
)
