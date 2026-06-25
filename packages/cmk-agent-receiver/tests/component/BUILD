load("@cmk_requirements//:requirements.bzl", "requirement")
load("//bazel/rules:py_cmk_test.bzl", "py_cmk_test")

py_cmk_test(
    name = "component",
    srcs = glob(["**/*.py"]),
    args = [
        "--random-order",
        "--random-order-bucket=global",
        "--durations=5",
    ],
    data = [
        "@remotejdk11_linux//:bin/java",
        "@wiremock_standalone//file",
    ],
    env = {
        "JAVA_BIN": "$(rootpath @remotejdk11_linux//:bin/java)",
        "WIREMOCK_JAR": "$(rootpath @wiremock_standalone//file)",
    },
    deps = [
        "//packages/cmk-agent-receiver",
        "//packages/cmk-agent-receiver:testlib",
        "//packages/cmk-crypto",
        requirement("pytest-xdist"),
        requirement("pytest-socket"),
        requirement("pytest-random-order"),
        requirement("fastapi"),
        requirement("starlette"),
        requirement("httpx"),
        requirement("python-dateutil"),
    ],
)
