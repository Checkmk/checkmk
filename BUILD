load("@bazel_skylib//rules:common_settings.bzl", "string_flag")
load("@hedron_compile_commands//:refresh_compile_commands.bzl", "refresh_compile_commands")
load("@repo_license//:license.bzl", "REPO_LICENSE")
load("@rules_python//python:pip.bzl", "compile_pip_requirements")

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

compile_pip_requirements(
    name = "requirements",
    timeout = "moderate",
    data = [
        "//packages/cmk-agent-based:requirements.txt",
        "//packages/cmk-agent-receiver:requirements.txt",
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
    env = {
        "PIPENV_PYPI_MIRROR": "https://pypi.org/simple",
    },
    extra_args = [
        "--no-strip-extras",  # reconsider this? (https://github.com/jazzband/pip-tools/issues/1613)
        "--quiet",
    ],
    requirements_in = ":requirements_cmk.txt",
    requirements_txt = "@//:requirements_lock.txt",
    tags = ["manual"],
    visibility = ["//visibility:public"],
)
