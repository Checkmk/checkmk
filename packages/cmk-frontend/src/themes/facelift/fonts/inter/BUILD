load("@@//bazel/rules:dependency_info.bzl", "dependency_info")
load("@aspect_bazel_lib//lib:copy_to_bin.bzl", "copy_to_bin")

dependency_info(
    name = "dependency_info",
    package_name = "inter",
    license_kind = "@package_metadata//licenses/spdx:OFL-1.1",
    purl_namespace = None,
    purl_type = "generic",
    version = "4.1",
)

copy_to_bin(
    name = "inter",
    srcs = glob(["*.woff2"]),
    package_metadata = [":dependency_info"],
    visibility = ["//packages/cmk-frontend:__pkg__"],
)
