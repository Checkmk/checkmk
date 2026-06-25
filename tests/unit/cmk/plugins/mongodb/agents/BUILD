load("@cmk_requirements//:requirements.bzl", "requirement")
load("//bazel/rules:py_cmk_test.bzl", "py_cmk_test")

py_cmk_test(
    name = "agents",
    size = "small",
    srcs = [
        "test_mk_mongodb.py",
    ],
    data = glob(["datasets/**"]),
    tags = ["legacy-python"],
    use_project_pytest_config = True,
    visibility = ["//visibility:private"],
    deps = [
        requirement("marshmallow"),
        requirement("pymongo"),
        "//cmk/plugins/mongodb/agents",
    ],
)
