load("@aspect_rules_js//js:defs.bzl", "js_library")
load("@bazel_skylib//rules:common_settings.bzl", "string_flag")
load("//bazel/rules:py_cmk_test.bzl", "py_cmk_test")

# The shared runner behind rust_wine_test() (xcomp/rust_wine_test.bzl).
exports_files(["xcomp/rust-test-wine.sh"])

js_library(
    name = "vitest_runner",
    srcs = ["vitest_runner.mjs"],
    visibility = ["//visibility:public"],
    deps = ["//:node_modules/vitest"],
)

# The tool invoked by sign_package.bzl's signing action.
exports_files(
    ["sign_package.sh"],
    visibility = ["//bazel/rules/sign_package_tests:__pkg__"],
)

# Absolute host paths consumed only by sign_package's own action - never by
# any other target, and never through --action_env. See sign_package.md.
string_flag(
    name = "signing_key_file",
    build_setting_default = "",
    visibility = ["//visibility:public"],
)

string_flag(
    name = "signing_key_passphrase_file",
    build_setting_default = "",
    visibility = ["//visibility:public"],
)

# Used by sign_package() to mark its targets incompatible until a key is
# configured. See sign_package.bzl/.md.
config_setting(
    name = "signing_key_file_unset",
    flag_values = {":signing_key_file": ""},
    visibility = ["//visibility:public"],
)

py_library(
    name = "runpath_patch",
    srcs = ["runpath_patch.py"],
    imports = ["."],
)

py_binary(
    name = "set_runpath_tree",
    srcs = ["set_runpath_tree.py"],
    visibility = ["//visibility:public"],
    deps = [":runpath_patch"],
)

py_binary(
    name = "set_runpath_whl",
    srcs = ["set_runpath_whl.py"],
    visibility = ["//visibility:public"],
    deps = [":runpath_patch"],
)

py_binary(
    name = "console_scripts_gen",
    srcs = ["console_scripts_gen.py"],
    visibility = ["//visibility:public"],
)

py_cmk_test(
    name = "unit",
    size = "small",
    srcs = ["console_scripts_gen_test.py"] + glob(["tests/*.py"]),
    imports = ["."],
    deps = [
        ":console_scripts_gen",
        ":set_runpath_tree",
        ":set_runpath_whl",
    ],
)
