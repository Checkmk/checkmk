load("@//bazel/rules:dependency_info.bzl", "dependency_info")
load("@aspect_bazel_lib//lib:copy_to_bin.bzl", "copy_to_bin")

dependency_info(
    name = "dependency_info",
    package_name = "jquery-mobile",
    license_kind = "@package_metadata//licenses/spdx:MIT",
    purl_namespace = None,
    purl_type = "npm",
    version = "1.4.5",
)

copy_to_bin(
    name = "jquery",
    srcs = glob([
        "**/*.*",
    ]),
    package_metadata = [":dependency_info"],
    visibility = ["//packages/cmk-frontend:__pkg__"],
)
