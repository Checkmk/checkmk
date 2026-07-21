load("@@//bazel/rules:dependency_info.bzl", "dependency_info")
load("@aspect_bazel_lib//lib:copy_to_bin.bzl", "copy_to_bin")

# https://commons.wikimedia.org/wiki/Category:Nuvola_icons
dependency_info(
    name = "dependency_info",
    package_name = "nuvola-icons",
    license_kind = "@package_metadata//licenses/spdx:LGPL-2.1-only",
    purl_namespace = None,
    purl_type = "generic",
    version = "1",
)

copy_to_bin(
    name = "nuvola-icons",
    srcs = glob([
        "icons/*.*",
    ]),
    package_metadata = [":dependency_info"],
    visibility = ["//packages/cmk-frontend:__pkg__"],
)
