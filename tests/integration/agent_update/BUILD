load("@cmk_requirements//:requirements.bzl", "requirement")
load("//bazel/rules:py_cmk_test.bzl", "py_cmk_test")

py_cmk_test(
    name = "agent_update",
    srcs = glob(["**/*.py"]),
    args = ["tests/integration/agent_update"],
    data = [
        "//packages/cmk-agent-ctl",
        "@remotejdk25_linux//:bin/java",
        "@wiremock_standalone//file",
    ],
    env = {
        "CMK_AGENT_CTL": "$(rootpath //packages/cmk-agent-ctl)",
        "JAVA_BIN": "$(rootpath @remotejdk25_linux//:bin/java)",
        "WIREMOCK_JAR": "$(rootpath @wiremock_standalone//file)",
    },
    deps = [
        "//packages/cmk-agent-receiver",
        "//packages/cmk-agent-receiver:testlib",
        "//packages/cmk-crypto",
        requirement("httpx2"),
    ],
)
