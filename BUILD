load("@bazel_skylib//rules:common_settings.bzl", "string_flag")
load("@bazel_skylib//rules:copy_file.bzl", "copy_file")
load("@hedron_compile_commands//:refresh_compile_commands.bzl", "refresh_compile_commands")
load("@repo_license//:license.bzl", "REPO_LICENSE")
load("@rules_proto//proto:defs.bzl", "proto_library")
load("@rules_uv//uv:pip.bzl", "pip_compile")
load("@rules_uv//uv:venv.bzl", "create_venv")

exports_files([
    "Pipfile",
    "Pipfile.lock",
    "pyproject.toml",
    "requirements.txt",
    "requirements_lock.txt",
])

string_flag(
    name = "cmk_version",
    build_setting_default = "UNSET",
    visibility = ["//:__subpackages__"],
)

string_flag(
    # For a discussion of Linux Standard Base (LSB) vs Filesystem Hierarchy Standard (FHS),
    # see https://lists.linux-foundation.org/pipermail/lsb-discuss/2011-February/006674.html
    #
    # Current state: debian-based distros use LSB and the others, including el{8,9} and sles
    # use FHS.
    name = "filesystem_layout",
    build_setting_default = "FILESYSTEM_LAYOUT_INVALID",
    visibility = ["//visibility:public"],
)

config_setting(
    name = "lsb_filesystem_layout",
    flag_values = {":filesystem_layout": "lsb"},
)

config_setting(
    name = "fhs_filesystem_layout",
    flag_values = {":filesystem_layout": "fhs"},
)

string_flag(
    name = "repo_license",
    build_setting_default = REPO_LICENSE,
    visibility = ["//visibility:public"],
)

config_setting(
    name = "gpl_repo",
    flag_values = {":repo_license": "gpl"},
)

config_setting(
    # We really mean the license here, editions are handled differently!
    name = "gpl+enterprise_repo",
    flag_values = {":repo_license": "gpl+enterprise"},
)

# Generate `compile_commands.json` with `bazel run //:refresh_compile_commands`.
refresh_compile_commands(
    name = "refresh_compile_commands",
    # TODO: Do we want that or not? We get quite a few duplicate entries which often differ without that option.
    # exclude_headers = "all",
    targets = {
        # target: build-flags
        "//packages/cmc:all": "",
        "//packages/livestatus:all": "",
        "//packages/neb:all": "",
        "//packages/unixcat:all": "",
    },
)

genrule(
    name = "_append_dependencies_from_pipfile",
    srcs = [
        ":requirements.txt",
        "//cmk:requirements.txt",
    ],
    outs = ["requirements_cmk.txt"],
    cmd = "cat $(location :requirements.txt) $(location //cmk:requirements.txt) > $@",
)

pip_compile(
    name = "requirements",
    data = [
        "//packages/cmk-agent-based:requirements.txt",
        "//packages/cmk-agent-receiver:requirements.txt",
        "//packages/cmk-ccc:requirements.txt",
        "//packages/cmk-crypto:requirements.txt",
        "//packages/cmk-graphing:requirements.txt",
        "//packages/cmk-livestatus-client:requirements.txt",
        "//packages/cmk-messaging:requirements.txt",
        "//packages/cmk-mkp-tool:requirements.txt",
        "//packages/cmk-rulesets:requirements.txt",
        "//packages/cmk-server-side-calls:requirements.txt",
        "//packages/cmk-shared-typing:requirements.txt",
        "//packages/cmk-trace:requirements.txt",
        "//packages/cmk-werks:requirements.txt",
    ],
    requirements_in = ":requirements_cmk.txt",
    requirements_txt = "@//:requirements_lock.txt",
    tags = ["manual"],
    visibility = ["//visibility:public"],
)

create_venv(
    name = "create_venv",
    destination_folder = ".venv_uv",
    requirements_txt = "@//:requirements_lock.txt",
)

copy_file(
    name = "_cmc_config_proto",
    src = "//non-free/cmc-protocols/protocols:checkmk/cmc/config/v1/types.proto",
    out = "cmc_proto/config/v1/types.proto",
)

copy_file(
    name = "_cmc_cycletime_proto",
    src = "//non-free/cmc-protocols/protocols:checkmk/cmc/cycletime/v1/types.proto",
    out = "cmc_proto/cycletime/v1/types.proto",
)

proto_library(
    name = "cycletime_proto",
    srcs = ["cmc_proto/cycletime/v1/types.proto"],
    strip_import_prefix = "cmc_proto",
    visibility = ["//visibility:public"],
)

proto_library(
    name = "config_proto",
    srcs = ["cmc_proto/config/v1/types.proto"],
    strip_import_prefix = "cmc_proto",
    visibility = ["//visibility:public"],
    deps = [
        ":cycletime_proto",
        "@com_google_protobuf//:duration_proto",
        "@com_google_protobuf//:timestamp_proto",
    ],
)
