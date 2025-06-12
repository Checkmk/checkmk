load("@bazel_skylib//rules:common_settings.bzl", "string_flag")
load("@bazel_skylib//rules:write_file.bzl", "write_file")
load("@com_google_protobuf//:protobuf_version.bzl", "PROTOBUF_PYTHON_VERSION")
load("@gazelle//:def.bzl", "gazelle")
load("@hedron_compile_commands//:refresh_compile_commands.bzl", "refresh_compile_commands")
load("@repo_license//:license.bzl", "REPO_LICENSE")
load("@rules_multirun//:defs.bzl", "multirun")
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
    name = "raw-requirements-in",
    constraints = [
        ":bazel-requirements-constraints.txt",
        ":requirements.txt",
        "//:constraints.txt",
    ],
    requirements = [
        "//cmk:requirements.in",
        "//packages:python_requirements",
        "//:dev-requirements.in",
    ],
)

pip_compile(
    name = "raw_requirements",
    requirements_in = ":raw-requirements-in",
    requirements_txt = ":raw-requirements.txt",
    tags = ["manual"],
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
)

multirun(
    name = "lock_python_requirements",
    commands = [
        ":requirements",
        ":raw_requirements",
        ":runtime_requirements",
    ],
    # Running in a single threaded mode allows consecutive `uv` invocations to benefit
    # from the `uv` cache from the first run.
    jobs = 1,
)

test_suite(
    name = "py_requirements_test_enterprise",
    tests = [
        ":raw_requirements_test",
        ":requirements_test",
        ":runtime_requirements_test",
    ],
)

test_suite(
    name = "py_requirements_test_gpl",
    tests = [":raw_requirements_test"],
)

write_file(
    # WHY?
    # * when creating a venv with bazel, we need to have everything sandbox-ed in bazel
    # * however we still want to use the packages somehow editable
    # * this is also important for the editors:
    #   changing signatures in package B which are consumed by package A must be picked up by e.g. mypy
    name = "sitecustomize",
    out = "sitecustomize.py",
    content = [
        "from pathlib import Path",
        "import sys",
        "",
        "repo_path = Path(__file__, '../../../../../').resolve()",
        "sys.path.insert(0, str(repo_path))",
        "",
        "def add_packages(from_path: Path) -> None:",
        "    sys.path = [",
        "        str(p)",
        "        for p in sorted(from_path.glob('packages/*'))",
        "        if p.joinpath('pyproject.toml').exists()",
        "    ] + sys.path",
        "",
        "add_packages(repo_path)",
    ] + select({
        "@//:gpl_repo": [],
        "@//:gpl+enterprise_repo": [
            "add_packages(repo_path.joinpath('non-free'))",
            # needed for composition tests: they want to 'import cmk_update_agent' via the .venv
            "sys.path.insert(0, str(repo_path.joinpath('non-free/packages/cmk-update-agent')))",
        ],
    }),
)

create_venv(
    name = "create_venv",
    destination_folder = ".venv",
    requirements_txt = select({
        "@//:gpl_repo": ":raw-requirements.txt",
        "@//:gpl+enterprise_repo": ":requirements.txt",
    }),
    site_packages_extra_files = [":sitecustomize.py"],
    whls = [
        "@rrdtool_native//:rrdtool_python_wheel",
        "//packages/cmk-shared-typing:wheel",
        "//packages/cmk-werks:wheel_entrypoint_only",
        "//packages/cmk-mkp-tool:wheel_entrypoint_only",
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

alias(
    name = "format",
    actual = "//bazel/tools:format",
    visibility = ["//visibility:public"],
)

alias(
    name = "format.check",
    actual = "//bazel/tools:format.check",
)
