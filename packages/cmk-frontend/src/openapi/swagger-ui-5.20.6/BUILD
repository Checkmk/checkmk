load("@aspect_bazel_lib//lib:copy_to_bin.bzl", "copy_to_bin")
load("@omd_packages//bazel/rules:dependency_info.bzl", "dependency_info")

dependency_info(
    name = "dependency_info",
    package_name = "swagger-ui",
    license_kind = "@package_metadata//licenses/spdx:Apache-2.0",
    purl_namespace = None,
    purl_type = "npm",
    version = "5.20.6",
)

copy_to_bin(
    name = "swagger-ui",
    srcs = glob([
        "**/*.*",
    ]),
    package_metadata = [":dependency_info"],
    visibility = ["//packages/cmk-frontend:__pkg__"],
)
