load("@aspect_rules_py//py:defs.bzl", "py_binary", "py_library")
load("@rules_pkg//pkg:mappings.bzl", "pkg_attributes", "pkg_files")

# Only for static analysis.
py_binary(
    name = "post-rename-site",
    srcs = ["post-rename-site.py"],
    main = "post-rename-site.py",
    visibility = ["//cmk:__pkg__"],
    deps = [":post_rename_site"],
)

pkg_files(
    name = "post-rename-site-pkg",
    srcs = ["post-rename-site.py"],
    attributes = pkg_attributes(
        mode = "0755",
    ),
    prefix = "bin",
    renames = {"post-rename-site.py": "post-rename-site"},
    visibility = ["//omd:__pkg__"],
)

py_library(
    name = "post_rename_site",
    srcs = [
        "logger.py",
        "main.py",
    ],
    imports = ["../.."],
    visibility = [
        "//bin:__subpackages__",
        "//cmk:__subpackages__",
        "//tests:__subpackages__",
    ],
    deps = [
        "//cmk/utils",
        "//packages/cmk-ccc:debug",
        "//packages/cmk-ccc:i18n",
        "//packages/cmk-ccc:site",
        "//packages/cmk-plugin-apis:discover_plugins",
        "//packages/cmk-plugin-apis:post_rename_site",
    ],
)
