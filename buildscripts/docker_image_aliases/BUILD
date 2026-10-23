load("@aspect_rules_py//py:defs.bzl", "py_binary")
load("@cmk_requirements//:requirements.bzl", "requirement")
load("//bazel/rules:py_cmk_test.bzl", "py_cmk_test")

package(default_visibility = ["//visibility:public"])

py_binary(
    name = "resolve",
    srcs = ["resolve.py"],
)

py_binary(
    name = "register",
    srcs = ["register.py"],
    deps = [
        requirement("docker"),
        requirement("pyyaml"),
    ],
)

sh_library(
    name = "docker_image_alias_sh",
    srcs = [
        "update.sh",
    ],
)

py_cmk_test(
    name = "unit",
    size = "small",
    srcs = glob(["tests/*.py"]),
    imports = ["."],
    deps = [
        ":register",
        ":resolve",
    ],
)
