load("@aspect_rules_py//py:defs.bzl", "py_binary")
load("@cmk_requirements//:requirements.bzl", "requirement")

package(default_visibility = ["//visibility:public"])

py_library(
    name = "lib",
    srcs = [
        "lib/__init__.py",
        "lib/common.py",
        "lib/registry.py",
    ],
    visibility = ["//visibility:private"],
    deps = [
        requirement("pyyaml"),
        requirement("docker"),
        requirement("requests"),
        "//packages/cmk-ccc:version",
        "//tests:testlib",
    ],
)

py_binary(
    name = "assert_build_artifacts",
    srcs = ["assert_build_artifacts.py"],
    deps = [
        ":lib",
        "//tests:testlib",
        requirement("requests"),
    ],
)

py_binary(
    name = "build-cmk-container",
    srcs = ["build-cmk-container.py"],
    deps = [
        ":lib",
        "//packages/cmk-ccc:archive",
        requirement("docker"),
    ],
)

py_binary(
    name = "get_distros",
    srcs = ["get_distros.py"],
    deps = [":lib"],
)

py_binary(
    name = "publish_cloud_images",
    srcs = ["publish_cloud_images.py"],
    deps = [
        "//packages/cmk-ccc:version",
        requirement("boto3"),
        requirement("azure-core"),
        requirement("azure-identity"),
        requirement("azure-mgmt-compute"),
        requirement("azure-mgmt-resource"),
    ],
)

py_binary(
    name = "unpublish-container-image",
    srcs = ["unpublish-container-image.py"],
    deps = [
        ":lib",
        "//packages/cmk-ccc:version",
    ],
)

py_binary(
    name = "validate_changes",
    srcs = ["validate_changes.py"],
    deps = [requirement("pyyaml")],
)

py_binary(
    name = "collect_mypy",
    srcs = ["collect_mypy.py"],
    main = "collect_mypy.py",
    tags = ["manual"],
)

filegroup(
    name = "groovy_files",
    srcs = glob(["**/*.groovy"]),
    tags = ["groovy"],
)

sh_library(
    name = "buildscripts_sh",
    srcs = [
        "bazel_execution_log_parser.sh",
        "bazel_mypy.sh",
        "bazel_test_non_cpp.sh",
        "bazel_test_post_archive_xunit.sh",
        "create_unsign_msi_patch.sh",
        "sign-packages.sh",
    ],
)
