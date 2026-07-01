load("@cmk_requirements//:requirements.bzl", "requirement")
load("//bazel/rules:py_cmk_test.bzl", "py_cmk_test")

py_cmk_test(
    name = "unit",
    size = "small",
    srcs = glob(["**/*.py"]),
    args = [
        "--random-order",
        "--random-order-bucket=global",
        "--disable-socket",
        "--allow-unix-socket",
        "--durations=5",
        "-W",
        "error",
    ],
    deps = [
        ":unit_testlib",
        "//packages/cmk-agent-receiver",
        "//packages/cmk-agent-receiver:testlib",
        requirement("cryptography"),
        requirement("fastapi"),
        requirement("httpx"),
        requirement("pytest-asyncio"),
        requirement("pytest-xdist"),
        requirement("pytest-socket"),
        requirement("pytest-random-order"),
        requirement("pytest-mock"),
        requirement("requests"),
        requirement("starlette"),
        requirement("time-machine"),
        requirement("python-dateutil"),
    ],
)

py_cmk_test(
    name = "unit_testlib",
    srcs = glob(["testlib/**/*.py"]),
    args = [
        "--random-order",
        "--random-order-bucket=global",
        "--durations=5",
    ],
    deps = [
        "//packages/cmk-agent-receiver:testlib",
        requirement("pytest-xdist"),
        requirement("httpx"),
        requirement("pytest-random-order"),
    ],
)
