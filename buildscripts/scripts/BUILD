load("@aspect_rules_py//py:defs.bzl", "py_binary")
load("@cmk_requirements//:requirements.bzl", "requirement")
load("//bazel/rules:py_cmk_test.bzl", "py_cmk_test")

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
        "//tests/testlib/common",
    ],
)

py_binary(
    name = "assert_build_artifacts",
    srcs = ["assert_build_artifacts.py"],
    deps = [
        "//packages/cmk-ccc:version",
        requirement("requests"),
    ],
)

py_binary(
    name = "build_cmk_container",
    srcs = ["build_cmk_container.py"],
    deps = [
        ":lib",
        "//packages/cmk-ccc:tar-archive",
        requirement("docker"),
    ],
)

py_binary(
    name = "check_no_remote_cache_tags",
    srcs = ["check_no_remote_cache_tags.py"],
)

py_binary(
    name = "check_thirdparty_modules",
    srcs = ["check_thirdparty_modules.py"],
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
    name = "unpublish_container_image",
    srcs = ["unpublish_container_image.py"],
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

py_library(
    name = "collect_mypy_lib",
    srcs = ["collect_mypy.py"],
)

py_binary(
    name = "collect_mypy",
    srcs = [":collect_mypy_lib"],
    tags = ["manual"],
)

py_library(
    name = "collect_rust_tests_lib",
    srcs = ["collect_rust_tests.py"],
)

py_binary(
    name = "collect_rust_tests",
    srcs = [":collect_rust_tests_lib"],
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
        "bazel_test_ci.sh",
        "bazel_test_post_archive_xunit.sh",
        "build_wine.sh",
        "check_community_edition_all_free.sh",
        "create_unsign_msi_patch.sh",
        "extract_llvm.sh",
        "sign-packages.sh",
    ],
)

py_cmk_test(
    name = "unit",
    size = "small",
    srcs = glob(["tests/*.py"]),
    imports = ["."],
    deps = [
        requirement("azure-mgmt-compute"),
        requirement("docker"),
        requirement("requests"),
        ":assert_build_artifacts",
        ":build_cmk_container",
        ":check_no_remote_cache_tags",
        ":check_thirdparty_modules",
        ":collect_mypy_lib",
        ":collect_rust_tests_lib",
        ":get_distros",
        ":lib",
        ":publish_cloud_images",
        ":unpublish_container_image",
        ":validate_changes",
    ],
)
