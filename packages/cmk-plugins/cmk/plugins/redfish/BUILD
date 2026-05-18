load("@aspect_rules_py//py:defs.bzl", "py_library")
load("@cmk_requirements//:requirements.bzl", "requirement")
load("@rules_pkg//pkg:mappings.bzl", "pkg_attributes", "pkg_files")
load("@rules_shell//shell:sh_library.bzl", "sh_library")
load("//omd/packages/Python:version.bzl", "PYTHON_MAJOR_DOT_MINOR")

py_library(
    name = "redfish",
    srcs = glob(["**/*.py"]),
    data = glob([
        "checkman/*",
        "libexec/*",
    ]) + ["py.typed"],
    imports = ["../../.."],
    visibility = ["//visibility:public"],
    deps = [
        "//packages/cmk-plugin-apis:agent_based",
        "//packages/cmk-plugin-apis:graphing",
        "//packages/cmk-plugin-apis:inventory_ui",
        "//packages/cmk-plugin-apis:password_store",
        "//packages/cmk-plugin-apis:rulesets",
        "//packages/cmk-plugin-apis:server_side_calls",
        "//packages/cmk-plugin-apis:server_side_programs",
        "//packages/cmk-plugins/cmk/plugins/lib",
        requirement("redfish"),
    ],
)

filegroup(
    name = "agent",
    srcs = glob(
        ["agent/**/*"],
        allow_empty = True,
    ),
    visibility = ["//packages/cmk-plugins:__pkg__"],
)

filegroup(
    name = "checkman",
    srcs = glob(
        ["checkman/**/*"],
        allow_empty = True,
    ),
    visibility = ["//packages/cmk-plugins:__pkg__"],
)

sh_library(
    name = "libexec",
    srcs = glob(
        ["libexec/*"],
        allow_empty = True,
    ),
    visibility = ["//packages/cmk-plugins:__pkg__"],
)

pkg_files(
    name = "libexec-for-pkg_tar",
    srcs = glob(
        ["libexec/*"],
        allow_empty = True,
    ),
    attributes = pkg_attributes(mode = "0755"),
    prefix = "lib/python%s/site-packages/cmk/plugins/redfish/libexec" % PYTHON_MAJOR_DOT_MINOR,
    visibility = ["//packages/cmk-plugins:__pkg__"],
)
