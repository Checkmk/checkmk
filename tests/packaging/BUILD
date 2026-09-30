load("@aspect_rules_py//py:defs.bzl", "py_library")
load("@cmk_requirements//:requirements.bzl", "requirement")

py_library(
    name = "packaging",
    testonly = True,
    srcs = glob(["**/*.py"]),
    imports = ["../.."],
    visibility = ["//tests:__subpackages__"],
    deps = [
        "//tests/testlib/common",
        "//tests/testlib/pytest_helpers",
        requirement("pytest"),
    ],
)

# Roots the Windows artifact signatures must chain to (Sectigo for the YubiKey
# path, Microsoft for Azure Artifact Signing and its timestamps).
filegroup(
    name = "signing_roots",
    srcs = glob(["certs/*.pem"]),
    visibility = ["//agents/wnx/scripts:__pkg__"],
)
