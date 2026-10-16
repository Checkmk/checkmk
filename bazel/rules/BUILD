load("@aspect_rules_js//js:defs.bzl", "js_library")
load("@bazel_skylib//rules:common_settings.bzl", "string_flag")
load("@rules_shell//shell:sh_binary.bzl", "sh_binary")
load("@rules_shell//shell:sh_library.bzl", "sh_library")
load("//bazel/rules:py_cmk_test.bzl", "py_cmk_test")

exports_files([
    # The shared runner behind rust_wine_test() (xcomp/rust_wine_test.bzl).
    "xcomp/rust-test-wine.sh",
    # Sourced by the scripts of package_msi.bzl rules.
    "xcomp/package_msi.sh",
])

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
# configured (see sign_package.bzl/.md), and by
# //:agent_package_signing_effectively_disabled to fall back to the unsigned
# agent .rpm.
config_setting(
    name = "signing_key_file_unset",
    flag_values = {":signing_key_file": ""},
    visibility = ["//visibility:public"],
)

# Absolute host path of the Azure Artifact Signing credentials, consumed only by
# the actions of sign_azure.bzl - never by any other target,
# and never through --action_env.
string_flag(
    name = "azure_signing_credentials_file",
    build_setting_default = "",
    visibility = ["//visibility:public"],
)

# Selects between the unsigned and the Azure-signed inputs of an MSI, and marks
# the sign_azure.bzl targets incompatible without credentials.
config_setting(
    name = "azure_signing_credentials_file_unset",
    flag_values = {":azure_signing_credentials_file": ""},
    visibility = ["//visibility:public"],
)

# Azure Artifact Signing: sign_azure signs files on the host (e.g. a finished
# MSI), the sign_azure.bzl rules sign inside a build. All of them sign and
# verify with azure_signing.sh.
sh_library(
    name = "azure_signing",
    srcs = ["azure_signing.sh"],
)

sh_binary(
    name = "sign_tar_azure",
    srcs = ["sign_tar_azure.sh"],
)

sh_binary(
    name = "sign_azure",
    srcs = ["sign_azure.sh"],
    data = [
        ":azure_signing",
        "//tests/packaging:signing_roots",
        "@osslsigncode",
        "@psign",
    ],
    env = {
        "SIGN_AZURE_LIB": "$(rlocationpath :azure_signing)",
        "SIGN_AZURE_OSSLSIGNCODE": "$(rlocationpath @osslsigncode)",
        "SIGN_AZURE_PSIGN": "$(rlocationpath @psign)",
        "SIGN_AZURE_ROOTS": "$(rlocationpaths //tests/packaging:signing_roots)",
    },
    # The launcher initializes the runfiles library and exports rlocation.
    use_bash_launcher = True,
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

py_binary(
    name = "deb_installed_size",
    srcs = ["deb_installed_size.py"],
    visibility = ["//visibility:public"],
)

py_cmk_test(
    name = "unit",
    size = "small",
    srcs = ["console_scripts_gen_test.py"] + glob(["tests/*.py"]),
    imports = ["."],
    deps = [
        ":console_scripts_gen",
        ":deb_installed_size",
        ":set_runpath_tree",
        ":set_runpath_whl",
    ],
)

# Lets shellcheck see these scripts. Nothing depends on this target.
sh_library(
    name = "shell_scripts",
    srcs = [
        "sign_package.sh",
        "xcomp/package_msi.sh",
    ],
)
