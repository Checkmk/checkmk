load("@aspect_bazel_lib//lib:copy_to_directory.bzl", "copy_to_directory")
load("@aspect_rules_js//js:defs.bzl", "js_library")
load("@bazel_skylib//rules:common_settings.bzl", "bool_flag", "string_flag")
load("@bazel_skylib//rules:write_file.bzl", "write_file")
load("@gazelle//:def.bzl", "gazelle")
load("@hedron_compile_commands//:refresh_compile_commands.bzl", "refresh_compile_commands")
load("@npm//:defs.bzl", "npm_link_all_packages")
load("@protobuf//:protobuf_version.bzl", "PROTOBUF_PYTHON_VERSION")
load("@repo_license//:license.bzl", "REPO_LICENSE")
load("@rules_multirun//:defs.bzl", "multirun")
load("@rules_uv//uv:pip.bzl", "pip_compile")
load("@rules_uv//uv:venv.bzl", "create_venv")
load("//bazel/rules:proto.bzl", "proto_library_as")
load("//bazel/rules:requirements.bzl", "compile_requirements_in")

exports_files(
    [
        ".clang-tidy",
        ".clippy.toml",
        ".npmrc",
        ".prettierignore",
        "AUTHORS",
        "COPYING",
        "pyproject.toml",
        "requirements.txt",
        ".shellcheckrc",
        ".stylelintrc.mjs",
        ".stylelintignore",
        "Cargo.toml",
        "Cargo.lock",
        "site.Cargo.lock.bazel",
        "host.Cargo.lock.bazel",
        ".cargo/config.toml",
        "module_layers.toml",
    ],
    visibility = ["//:__subpackages__"],
)

js_library(
    name = "stylelintrc",
    srcs = [
        ".stylelintignore",
        ".stylelintrc.mjs",
    ],
    visibility = ["//:__subpackages__"],
    deps = [
        "//:node_modules/postcss-html",
        "//:node_modules/stylelint-config-standard",
        "//packages/cmk-frontend-vue:stylelint_plugin",
    ],
)

filegroup(
    name = "buildifier_config",
    srcs = [".buildifier.json"],
    visibility = ["//visibility:public"],
)

npm_link_all_packages(name = "node_modules")

copy_to_directory(
    name = "werks_group",
    srcs = glob([".werks/*"]),
    out = "werks_dir",
    root_paths = [".werks"],
    visibility = ["//:__subpackages__"],
)

string_flag(
    name = "repo_license",
    build_setting_default = REPO_LICENSE,
    visibility = ["//visibility:public"],
)

bool_flag(
    name = "use_faked_artifacts",
    build_setting_default = False,
    visibility = ["//visibility:public"],
)

config_setting(
    name = "use_fake_artifacts_enabled",
    flag_values = {":use_faked_artifacts": "True"},
    visibility = ["//visibility:public"],
)

bool_flag(
    name = "skip_package_compression",
    build_setting_default = False,
    visibility = ["//visibility:public"],
)

config_setting(
    name = "skip_package_compression_enabled",
    flag_values = {":skip_package_compression": "True"},
    visibility = ["//visibility:public"],
)

config_setting(
    name = "gpl_repo",
    flag_values = {":repo_license": "gpl"},
    visibility = ["//:__subpackages__"],
)

config_setting(
    # We really mean the license here, editions are handled differently!
    name = "gpl+nonfree_repo",
    flag_values = {":repo_license": "gpl+enterprise"},
    visibility = ["//:__subpackages__"],
)

# Generate `compile_commands.json` with `bazel run //:refresh_compile_commands`.
refresh_compile_commands(
    name = "refresh_compile_commands",
    exclude_external_sources = True,
    exclude_headers = "all",
    tags = [
        "manual",
        "no-mypy",
    ],
    targets = {
        # target: build-flags
        "//non-free/packages/cmc:all": "",
        "//packages/livestatus:all": "",
        "//packages/neb:all": "",
        "//packages/unixcat:all": "",
    },
)

write_file(
    name = "bazel-requirements-constraints",
    out = "bazel-requirements-constraints.txt",
    content = [
        "ruff==0.15.8",  # keep in sync with the multitool hub % RUFF_VERSION,
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
        "//agents/plugins:dev-requirements.in",
        "//cmk:requirements.in",
        "//.github/skills:dev-requirements.in",
        "//packages:dev_python_requirements",
        "//packages:python_requirements",
        "//scripts:requirements.in",
        "//tests:dev-requirements.in",
    ] + select({
        "@//:gpl+nonfree_repo": [
            "//non-free/packages:python_requirements",
            "//non-free/packages:dev_python_requirements",
        ],
        "@//:gpl_repo": [],
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
    name = "community-requirements-in",
    constraints = [
        ":bazel-requirements-constraints.txt",
        ":requirements.txt",
        "//:constraints.txt",
    ],
    requirements = [
        "//scripts:requirements.in",
        "//cmk:requirements.in",
        "//tests:dev-requirements.in",
        "//packages:python_requirements",
    ],
)

pip_compile(
    name = "community_requirements",
    requirements_in = ":community-requirements-in",
    requirements_txt = ":community-requirements.txt",
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
        "@//:gpl+nonfree_repo": ["//non-free/packages:python_requirements"],
        "@//:gpl_repo": [],
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
        ":community_requirements",
        ":runtime_requirements",
    ] + select({
        "@//:gpl+nonfree_repo": ["//omd/non-free/relay:requirements"],
        "@//:gpl_repo": [],
    }),
    # Running in a single threaded mode allows consecutive `uv` invocations to benefit
    # from the `uv` cache from the first run.
    jobs = 1,
)

test_suite(
    name = "py_requirements_test_nonfree",
    tests = [
        ":community_requirements_test",
        ":requirements_test",
        ":runtime_requirements_test",
    ],
)

test_suite(
    name = "py_requirements_test_gpl",
    tests = [":community_requirements_test"],
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
        "@//:gpl+nonfree_repo": [
            "add_packages(repo_path.joinpath('non-free'))",
            # needed for composition tests: they want to 'import cmk_update_agent' via the .venv
            "sys.path.insert(0, str(repo_path.joinpath('non-free/packages/cmk-update-agent')))",
        ],
        "@//:gpl_repo": [],
    }),
)

create_venv(
    name = "create_venv",
    destination_folder = ".venv",
    requirements_txt = select({
        "@//:gpl+nonfree_repo": ":requirements.txt",
        "@//:gpl_repo": ":community-requirements.txt",
    }),
    site_packages_extra_files = [":sitecustomize.py"],
    whls = [
        "@rrdtool_native//:rrdtool_python_wheel",
        "//packages/cmk-shared-typing:wheel",
        "//packages/cmk-werks:wheel_entrypoint_only",
        "//packages/cmk-mkp-tool:wheel_entrypoint_only",
    ] + select({
        "@//:gpl+nonfree_repo": [
            "//non-free/packages/cmc-protocols:wheel",
        ],
        "@//:gpl_repo": [],
    }),
)

write_file(
    name = "empty_proto",
    out = "empty_proto.proto",
    content = ['syntax = "proto2";'],
)

proto_library_as(
    name = "cycletime_proto",
    as_proto = "cmc_proto/cycletime.proto",
    proto = select({
        "@//:gpl+nonfree_repo": "//non-free/packages/cmc-protocols/protocols:cmc_config/cycletime.proto",
        "@//:gpl_repo": ":empty_proto",
    }),
    visibility = ["//visibility:public"],
)

proto_library_as(
    name = "config_proto",
    as_proto = "cmc_proto/config.proto",
    proto = select({
        "@//:gpl+nonfree_repo": "//non-free/packages/cmc-protocols/protocols:cmc_config/config.proto",
        "@//:gpl_repo": ":empty_proto",
    }),
    visibility = ["//visibility:public"],
    deps = [
        ":cycletime_proto",
        "@protobuf//:duration_proto",
        "@protobuf//:timestamp_proto",
    ],
)

proto_library_as(
    name = "state_proto",
    as_proto = "cmc_proto/state.proto",
    proto = select({
        "@//:gpl+nonfree_repo": "//non-free/packages/cmc-protocols/protocols:cmc_config/state.proto",
        "@//:gpl_repo": ":empty_proto",
    }),
    visibility = ["//visibility:public"],
    deps = [
        ":cycletime_proto",
        "@protobuf//:duration_proto",
        "@protobuf//:timestamp_proto",
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

sh_library(
    name = "root_sh",
    srcs = [
        "buildscripts/infrastructure/build-nodes/agent-builder/build-image-32.sh",
        "buildscripts/infrastructure/build-nodes/agent-builder/build-image-64.sh",
        "buildscripts/infrastructure/build-nodes/agent-builder/build-image-windows.sh",
        "buildscripts/infrastructure/build-nodes/scripts/checksums",
        "buildscripts/infrastructure/build-nodes/scripts/install-aws-cli.sh",
        "buildscripts/infrastructure/build-nodes/scripts/install-bazel.sh",
        "buildscripts/infrastructure/build-nodes/scripts/install-cmake.sh",
        "buildscripts/infrastructure/build-nodes/scripts/install-cmk-dependencies.sh",
        "buildscripts/infrastructure/build-nodes/scripts/install-development.sh",
        "buildscripts/infrastructure/build-nodes/scripts/install-docker.sh",
        "buildscripts/infrastructure/build-nodes/scripts/install-gdb.sh",
        "buildscripts/infrastructure/build-nodes/scripts/install-gnu-toolchain.sh",
        "buildscripts/infrastructure/build-nodes/scripts/install-make-dist-deps.sh",
        "buildscripts/infrastructure/build-nodes/scripts/install-openssl.sh",
        "buildscripts/infrastructure/build-nodes/scripts/install-packer.sh",
        "buildscripts/infrastructure/build-nodes/scripts/install-patchelf.sh",
        "buildscripts/infrastructure/build-nodes/scripts/install-protobuf-cpp.sh",
        "buildscripts/infrastructure/build-nodes/scripts/install-pyenv.sh",
        "buildscripts/infrastructure/build-nodes/scripts/install-python.sh",
        "buildscripts/infrastructure/build-nodes/scripts/install-valgrind.sh",
        "defines/dev-images/entrypoint.sh",
        "defines/dev-images/populate-build-context.sh",
        "defines/dev-images/reference-image-id",
        "docker_image/docker-entrypoint.sh",
        "packer/example_build.sh",
        "third_party/asio/create-archive",
        "third_party/fmt/create-archive",
        "third_party/googletest/create-archive",
        "third_party/openhardwaremonitor/create-archive",
        "third_party/re2/create-archive",
        "third_party/rrdtool/create-archive",
        "third_party/simpleini/create-archive",
        "third_party/yaml-cpp/create-archive",
        ":build_lib_sh",
    ],
    visibility = ["//visibility:public"],
)

sh_library(
    name = "build_lib_sh",
    srcs = [
        "buildscripts/infrastructure/build-nodes/scripts/build_lib.sh",
    ],
    visibility = ["//visibility:public"],
)

js_library(
    name = "eslintrc",
    srcs = ["eslint.config.mjs"],
    visibility = ["//:__subpackages__"],
    deps = [
        ":node_modules/@eslint/js",
        ":node_modules/@vue/eslint-config-prettier",
        ":node_modules/@vue/eslint-config-typescript",
        ":node_modules/eslint-plugin-vue",
        ":node_modules/typescript-eslint",
    ],
)

alias(
    name = "format",
    actual = "//bazel/tools/format",
    visibility = ["//visibility:public"],
)

alias(
    name = "format.check",
    actual = "//bazel/tools/format:check",
)

alias(
    name = "buildifier",
    actual = "//bazel/tools:buildifier",
)

alias(
    name = "buildifier.check",
    actual = "//bazel/tools:buildifier.check",
)
