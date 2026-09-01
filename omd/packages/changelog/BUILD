load("@bazel_skylib//rules:run_binary.bzl", "run_binary")
load("@rules_pkg//pkg:mappings.bzl", "pkg_files")
load("@rules_pkg//pkg:tar.bzl", "pkg_tar")

run_binary(
    name = "run_werks_precompile_community",
    srcs = ["//:werks_group"],
    outs = ["werks_precompiled_community"],
    args = [
        "precompile",
        "$(location //:werks_group)/werks",
        "--filter-by-edition",
        "community",
        "$(location werks_precompiled_community)",
    ],
    tags = ["manual"],
    tool = "//packages/cmk-werks:utils-bin",
)

run_binary(
    name = "run_werks_precompile_pro",
    srcs = ["//:werks_group"],
    outs = ["werks_precompiled_pro"],
    args = [
        "precompile",
        "$(location //:werks_group)/werks",
        "--filter-by-edition",
        "pro",
        "$(location werks_precompiled_pro)",
    ],
    tags = ["manual"],
    tool = "//packages/cmk-werks:utils-bin",
)

run_binary(
    name = "run_werks_precompile_ultimate",
    srcs = ["//:werks_group"],
    outs = ["werks_precompiled_ultimate"],
    args = [
        "precompile",
        "$(location //:werks_group)/werks",
        "--filter-by-edition",
        "ultimate",
        "$(location werks_precompiled_ultimate)",
    ],
    tags = ["manual"],
    tool = "//packages/cmk-werks:utils-bin",
)

run_binary(
    name = "run_werks_precompile_cloud",
    srcs = ["//:werks_group"],
    outs = ["werks_precompiled_cloud"],
    args = [
        "precompile",
        "$(location //:werks_group)/werks",
        "--filter-by-edition",
        "cloud",
        "$(location werks_precompiled_cloud)",
    ],
    tags = ["manual"],
    tool = "//packages/cmk-werks:utils-bin",
)

run_binary(
    name = "run_werks_precompile_ultimatemt",
    srcs = ["//:werks_group"],
    outs = ["werks_precompiled_ultimatemt"],
    args = [
        "precompile",
        "$(location //:werks_group)/werks",
        "--filter-by-edition",
        "ultimatemt",
        "$(location werks_precompiled_ultimatemt)",
    ],
    tags = ["manual"],
    tool = "//packages/cmk-werks:utils-bin",
)

# One pkg_files per edition, each ships only that edition's werks under its own filename.
# The pkg_tar select below composes the right set for each edition (layering).
pkg_files(
    name = "werks_pkg_community",
    srcs = [":werks_precompiled_community"],
    prefix = "share/check_mk/werks",
    renames = {":werks_precompiled_community": "werks"},
    tags = ["manual"],
)

pkg_files(
    name = "werks_pkg_pro",
    srcs = [":werks_precompiled_pro"],
    prefix = "share/check_mk/werks",
    renames = {":werks_precompiled_pro": "werks-pro"},
    tags = ["manual"],
)

pkg_files(
    name = "werks_pkg_ultimate",
    srcs = [":werks_precompiled_ultimate"],
    prefix = "share/check_mk/werks",
    renames = {":werks_precompiled_ultimate": "werks-ultimate"},
    tags = ["manual"],
)

pkg_files(
    name = "werks_pkg_cloud",
    srcs = [":werks_precompiled_cloud"],
    prefix = "share/check_mk/werks",
    renames = {":werks_precompiled_cloud": "werks-cloud"},
    tags = ["manual"],
)

pkg_files(
    name = "werks_pkg_ultimatemt",
    srcs = [":werks_precompiled_ultimatemt"],
    prefix = "share/check_mk/werks",
    renames = {":werks_precompiled_ultimatemt": "werks-ultimatemt"},
    tags = ["manual"],
)

pkg_tar(
    name = "changelog",
    srcs = select({
        "@cmk//edition:cloud": [
            "werks_pkg_cloud",
            "werks_pkg_community",
            "werks_pkg_pro",
            "werks_pkg_ultimate",
        ],
        "@cmk//edition:community": [
            "werks_pkg_community",
        ],
        "@cmk//edition:pro": [
            "werks_pkg_community",
            "werks_pkg_pro",
        ],
        "@cmk//edition:ultimate": [
            "werks_pkg_community",
            "werks_pkg_pro",
            "werks_pkg_ultimate",
        ],
        "@cmk//edition:ultimatemt": [
            "werks_pkg_community",
            "werks_pkg_pro",
            "werks_pkg_ultimate",
            "werks_pkg_ultimatemt",
        ],
    }),
    stamp = 1,
    tags = ["manual"],
    visibility = ["@@//omd:__subpackages__"],
)
