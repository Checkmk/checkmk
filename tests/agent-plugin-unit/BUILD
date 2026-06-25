load("@cmk_requirements//:requirements.bzl", "requirement")
load("//bazel/rules:py_cmk_test.bzl", "py_cmk_test")

py_cmk_test(
    name = "agent-plugin-unit",
    # https://bazel.build/reference/be/common-definitions#test.size
    size = "small",
    srcs = glob(["**/*.py"]),
    args = [
        "--random-order-bucket=global",
    ],
    data = glob(["datasets/**"]),
    tags = ["legacy-python"],
    use_project_pytest_config = True,
    visibility = ["//visibility:private"],
    deps = [
        requirement("pytest-mock"),
        requirement("pytest-asyncio"),
        requirement("pytest-random-order"),
        requirement("pymongo"),
        requirement("marshmallow"),
        "//agents/plugins:agent-plugins-python",
    ],
)
