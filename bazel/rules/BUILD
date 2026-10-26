load("@aspect_rules_py//py:defs.bzl", "py_pytest_main", "py_test")
load("@bazel_skylib//rules:common_settings.bzl", "string_flag")
load("@cmk_requirements//:requirements.bzl", "requirement")
load("@rules_shell//shell:sh_binary.bzl", "sh_binary")
load("@rules_shell//shell:sh_library.bzl", "sh_library")

exports_files([
    # The shared runner behind rust_wine_test() (xcomp/rust_wine_test.bzl).
    "xcomp/rust-test-wine.sh",
    # Sourced by the scripts of package_msi.bzl rules.
    "xcomp/package_msi.sh",
])

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
    name = "sign_file_azure",
    srcs = ["sign_file_azure.sh"],
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

py_binary(
    name = "set_runpath_tree",
    srcs = ["set_runpath_tree.py"],
    visibility = ["//visibility:public"],
)

py_binary(
    name = "deb_installed_size",
    srcs = ["deb_installed_size.py"],
    visibility = ["//visibility:public"],
)

py_pytest_main(
    name = "__test__",
    deps = [requirement("pytest")],
)

py_test(
    name = "unit",
    size = "small",
    srcs = glob(["tests/*.py"]) + [":__test__.py"],
    imports = ["."],
    main = "__test__.py",
    deps = [
        ":__test__",
        ":deb_installed_size",
        requirement("pytest"),
    ],
)

# Lets shellcheck see these scripts. Nothing depends on this target.
sh_library(
    name = "shell_scripts",
    srcs = ["xcomp/package_msi.sh"],
)
