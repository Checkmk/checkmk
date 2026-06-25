load("@cmk_requirements//:requirements.bzl", "requirement")
load("//bazel/rules:py_cmk_test.bzl", "py_cmk_test")

py_cmk_test(
    name = "testlib",
    srcs = glob(["**/*.py"]),
    args = [
        "--random-order-bucket=global",
        "--dist=loadfile",
        "--numprocesses=4",
    ],
    use_project_pytest_config = True,
    visibility = ["//visibility:private"],
    deps = [
        "//tests/testlib:testlib_system_level",
        requirement("docker"),
        requirement("pytest-random-order"),
        # pytest-xdist for `--numprocesses=NPROC`
        requirement("pytest-xdist"),
    ],
)
