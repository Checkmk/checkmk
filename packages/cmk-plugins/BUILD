load("@bazel_skylib//rules:build_test.bzl", "build_test")
load("@rules_pkg//pkg:tar.bzl", "pkg_tar")
load("@rules_python//python:packaging.bzl", "py_wheel")
load("@rules_shell//shell:sh_library.bzl", "sh_library")
load("//:relay_supported_plugins.bzl", "RELAY_SUPPORTED_PLUGIN_FAMILIES")
load("//bazel/rules:concat_files.bzl", "concat_files")
load("//bazel/rules:doctest.bzl", "py_doc_test")
load("//bazel/rules:package_wheel.bzl", "package_wheel")

# This detects the plugin families automatically.
# Each subdirectory in cmk/plugins/ is considered a family.
# In most cases it should be sufficient to add the two targets `:<family>` and `:<family>-test`
# Sorting them alphabetically would be nice. Thank you :-)

FAMILIES = [
    pkg.removeprefix("cmk/plugins/")
    for pkg in subpackages(include = ["cmk/plugins/*"])
]

exports_files([
    "dev-requirements.in",
    "pyproject.toml",
] + [
    "requirements.in-%s" % family
    for family in FAMILIES
])

concat_files(
    name = "requirements.in",
    srcs = [
        ":requirements.in-%s" % family
        for family in FAMILIES
    ],
    visibility = ["//visibility:public"],
)

[py_wheel(
    name = "wheel-for-f12-%s" % family,
    distribution = "cmk-plugins-%s-f12" % family,
    entry_points = {
        "cmk.special_agent_supported_on_relay": [
            "%s = %s" % (family, family),
        ] if family in RELAY_SUPPORTED_PLUGIN_FAMILIES else [],
    },
    strip_path_prefixes = ["packages/cmk-plugins"],
    tags = ["manual"],
    version = "1.0.0",
    deps = [
        "//packages/cmk-plugins/cmk/plugins/%s" % family,
        "//packages/cmk-plugins/cmk/plugins/%s:agent" % family,
        "//packages/cmk-plugins/cmk/plugins/%s:checkman" % family,
        "//packages/cmk-plugins/cmk/plugins/%s:libexec" % family,
    ],
) for family in FAMILIES]

[py_wheel(
    name = "wheel-for-pkg_tar-%s" % family,
    distribution = "cmk-plugins-%s-tar" % family,
    entry_points = {
        "cmk.special_agent_supported_on_relay": [
            "%s = %s" % (family, family),
        ] if family in RELAY_SUPPORTED_PLUGIN_FAMILIES else [],
    },
    strip_path_prefixes = ["packages/cmk-plugins"],
    version = "1.0.0",
    deps = [
        "//packages/cmk-plugins/cmk/plugins/%s" % family,
        "//packages/cmk-plugins/cmk/plugins/%s:agent" % family,
        "//packages/cmk-plugins/cmk/plugins/%s:checkman" % family,
    ],
) for family in FAMILIES]

build_test(
    name = "build_test",
    targets = ["wheel-for-f12-{}".format(family) for family in FAMILIES] + [
        "wheel-for-pkg_tar-{}".format(family)
        for family in FAMILIES
    ],
)

# Here comes the HACK to work around CMK-27714.
# `package_wheel` will not preserve the +x flag
# on the libexec files.
# To fix this we
# * create a dedicated wheel *without* the libexec files
# * add an additional target to contain *just* the libexec files
# * build the pkg_tar from those.
# Once `package_wheel` is fixed, this can be simplified.
[package_wheel(
    name = "pkg_tar-%s" % family,
    additional_files = [
        "//packages/cmk-plugins/cmk/plugins/%s:libexec-for-pkg_tar" % family,
    ],
    visibility = ["//visibility:public"],
    whl = "wheel-for-pkg_tar-%s" % family,
) for family in FAMILIES]

pkg_tar(
    name = "pkg_tar",
    stamp = 1,
    visibility = ["//visibility:public"],
    deps = [":pkg_tar-%s" % family for family in FAMILIES],
)

[alias(
    name = family,
    actual = "//packages/cmk-plugins/cmk/plugins/%s:%s" % (family, family),
    visibility = ["//visibility:public"],
) for family in FAMILIES]

sh_library(
    name = "helpers",
    srcs = [
        ".f12",
        "run",
    ],
)

py_doc_test(
    name = "doctest",
    size = "small",
    srcs = ["//packages/cmk-plugins/cmk/plugins/%s:%s" % (family, family) for family in FAMILIES],
    tags = ["no-mypy"],
)
