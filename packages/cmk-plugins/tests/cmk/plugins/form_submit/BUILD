load("@cmk_requirements//:requirements.bzl", "requirement")
load("//bazel/rules:py_cmk_test.bzl", "py_cmk_test")

py_cmk_test(
    name = "form_submit-test",
    size = "small",
    srcs = glob(["**/*.py"]),
    data = glob(
        ["**/*"],
        exclude = [
            "**/*.py",
            "BUILD",
            "**/OWNERS",
        ],
    ),
    deps = [
        "//packages/cmk-plugins/cmk/plugins/form_submit",
        requirement("vcrpy"),
    ],
)
