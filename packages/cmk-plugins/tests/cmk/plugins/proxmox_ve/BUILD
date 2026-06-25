load("@cmk_requirements//:requirements.bzl", "requirement")
load("//bazel/rules:py_cmk_test.bzl", "py_cmk_test")

py_cmk_test(
    name = "proxmox_ve-test",
    size = "small",
    srcs = glob(["**/*.py"]),
    data = glob(["**/files/**"]),
    deps = [
        "//packages/cmk-plugins/cmk/plugins/proxmox_ve",
        requirement("time-machine"),
    ],
)
