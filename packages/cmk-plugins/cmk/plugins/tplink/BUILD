load("@aspect_rules_py//py:defs.bzl", "py_library")
load("@rules_pkg//pkg:mappings.bzl", "pkg_attributes", "pkg_files")
load("@rules_shell//shell:sh_library.bzl", "sh_library")
load("//omd/packages/Python:version.bzl", "PYTHON_MAJOR_DOT_MINOR")

py_library(
    name = "tplink",
    srcs = glob(["**/*.py"]),
    data = glob(
        [
            "checkman/*",
        ],
    ) + ["py.typed"],
    imports = ["../../.."],
    visibility = ["//visibility:public"],
    deps = [
        "//packages/cmk-plugin-apis:agent_based",
        "//packages/cmk-plugins/cmk/plugins/lib",
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
    prefix = "lib/python%s/site-packages/cmk/plugins/tplink/libexec" % PYTHON_MAJOR_DOT_MINOR,
    visibility = ["//packages/cmk-plugins:__pkg__"],
)
