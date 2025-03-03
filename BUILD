load("@bazel_skylib//rules:common_settings.bzl", "string_flag")
load("@bazel_skylib//rules:write_file.bzl", "write_file")
load("@com_google_protobuf//:protobuf_version.bzl", "PROTOBUF_PYTHON_VERSION")
load("@gazelle//:def.bzl", "gazelle")
load("@hedron_compile_commands//:refresh_compile_commands.bzl", "refresh_compile_commands")
load("@repo_license//:license.bzl", "REPO_LICENSE")
load("@rules_uv//uv:pip.bzl", "pip_compile")
load("@rules_uv//uv:venv.bzl", "create_venv")
load("//:bazel_variables.bzl", "RUFF_VERSION")
load("//bazel/rules:copy_to_directory.bzl", "copy_to_directory")
load("//bazel/rules:proto.bzl", "proto_library_as")
load("//bazel/rules:requirements.bzl", "compile_requirements_in")

exports_files(
    [
        "pyproject.toml",
        "requirements.txt",
    ],
)

copy_to_directory(
    name = "werks_group",
    srcs = glob([".werks/*"]),
    out_dir = "werks_dir",
    visibility = ["//:__subpackages__"],
)

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

write_file(
    name = "bazel-requirements-constraints",
    out = "bazel-requirements-constraints.txt",
    content = [
        "ruff==%s" % RUFF_VERSION,
        "protobuf==%s" % PROTOBUF_PYTHON_VERSION,
    ],
)

compile_requirements_in(
    name = "requirements-in",
    constraints = [
        ":bazel-requirements-constraints.txt",
        "//:constraints.txt",
    ],
    requirements = [
        "//cmk:requirements.in",
        "//packages:python_requirements",
        "//:dev-requirements.in",
    ] + select({
        "@//:gpl_repo": [],
        "@//:gpl+enterprise_repo": ["//non-free/packages:python_requirements"],
    }),
)

pip_compile(
    name = "requirements",
    requirements_in = ":requirements-in",
    requirements_txt = "@//:requirements.txt",
    tags = ["manual"],
    visibility = ["//visibility:public"],
)

compile_requirements_in(
    name = "runtime-requirements-in",
    constraints = [
        ":bazel-requirements-constraints.txt",
        ":requirements.txt",
        "//:constraints.txt",
    ],
    requirements = [
        "//cmk:requirements.in",
        "//packages:python_requirements",
    ] + select({
        "@//:gpl_repo": [],
        "@//:gpl+enterprise_repo": ["//non-free/packages:python_requirements"],
    }),
)

pip_compile(
    name = "runtime_requirements",
    requirements_in = ":runtime-requirements-in",
    requirements_txt = ":runtime-requirements.txt",
    tags = ["manual"],
    visibility = ["//visibility:public"],
)

test_suite(
    name = "requirements_test_suite",
    tests = [
        ":requirements_test",
        ":runtime_requirements_test",
    ],
)

write_file(
    # WHY?
    # * when creating a venv with bazel, we need to have everything sandbox-ed in bazel
    # * however we still want to use the packages somehow editable
    name = "sitecustomize",
    out = "sitecustomize.py",
    content = [
        "import os",
        "import sys",
        "dirname = os.path.dirname(__file__)",
        'sys.path.append(os.path.abspath(os.path.join(dirname, "../../../../")))',
        'relative_packages_path = "../../../../packages"',
        "for p in os.listdir(os.path.join(dirname, relative_packages_path)):",
        "    sys.path.append(os.path.abspath(os.path.join(dirname, relative_packages_path, p)))",
    ] + select({
        "@//:gpl_repo": [],
        "@//:gpl+enterprise_repo": [
            'relative_packages_path_non_free = "../../../../non-free/packages"',
            "for p in os.listdir(os.path.join(dirname, relative_packages_path_non_free)):",
            "    sys.path.append(os.path.abspath(os.path.join(dirname, relative_packages_path_non_free, p)))",
        ],
    }),
)

create_venv(
    name = "create_venv",
    destination_folder = ".venv",
    requirements_txt = "@//:requirements.txt",
    site_packages_extra_files = [":sitecustomize.py"],
    whls = [
        "@rrdtool_native//:rrdtool_python_wheel",
    ] + select({
        "@//:gpl_repo": [],
        "@//:gpl+enterprise_repo": [
            "//non-free/packages/cmc-protocols:wheel",
        ],
    }),
)

proto_library_as(
    name = "cycletime_proto",
    as_proto = "cmc_proto/cycletime.proto",
    proto = "//non-free/packages/cmc-protocols/protocols:cmc_config/cycletime.proto",
    visibility = ["//visibility:public"],
)

proto_library_as(
    name = "config_proto",
    as_proto = "cmc_proto/config.proto",
    proto = "//non-free/packages/cmc-protocols/protocols:cmc_config/config.proto",
    visibility = ["//visibility:public"],
    deps = [
        ":cycletime_proto",
        "@com_google_protobuf//:duration_proto",
        "@com_google_protobuf//:timestamp_proto",
    ],
)

proto_library_as(
    name = "state_proto",
    as_proto = "cmc_proto/state.proto",
    proto = "//non-free/packages/cmc-protocols/protocols:cmc_config/state.proto",
    visibility = ["//visibility:public"],
    deps = [
        ":cycletime_proto",
        "@com_google_protobuf//:duration_proto",
        "@com_google_protobuf//:timestamp_proto",
    ],
)

gazelle(
    name = "gazelle-update-repos",
    args = [
        "-from_file=non-free/packages/otel-collector/go.mod",
    ],
    command = "update-repos",
)

gazelle(
    name = "gazelle",
)
