load("@cmk_requirements//:requirements.bzl", "requirement")
load("//bazel/rules:py_cmk_test.bzl", "py_cmk_test")

py_cmk_test(
    name = "agents",
    # https://bazel.build/reference/be/common-definitions#test.size
    size = "small",
    srcs = [
        "test_plesk_backups.py",
        "test_plesk_domains.py",
    ],
    tags = ["legacy-python"],
    use_project_pytest_config = True,
    visibility = ["//visibility:private"],
    deps = [
        requirement("marshmallow"),
        "//cmk/plugins/plesk/agents",
    ],
)
