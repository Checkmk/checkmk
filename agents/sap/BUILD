load("@//bazel/rules:dependency_info.bzl", "dependency_info")

dependency_info(
    name = "dependency_info",
    package_name = "sapnwrfc",
    license_kind = "@package_metadata//licenses/spdx:LGPL-2.1-only",
    purl_namespace = None,
    purl_type = "pypi",
    version = "0.19",
)

filegroup(
    name = "srcs",
    srcs = [
        "sap.cfg",
        "sapnwrfc-0.19.tar.gz",
    ],
    package_metadata = [":dependency_info"],
    visibility = ["//visibility:public"],
)
