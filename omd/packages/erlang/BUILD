load("@rules_pkg//pkg:mappings.bzl", "filter_directory", "pkg_attributes", "pkg_files", "pkg_mklink", "strip_prefix")
load("@rules_pkg//pkg:tar.bzl", "pkg_tar")
load("//bazel/rules:exclude_from_filegroup.bzl", "exclude_from_filegroup")
load("//omd/packages/erlang:vars.bzl", "PLACE_HOLDER")

OMD_ROOT_AWARE = [
    "lib/erlang/bin/erl",
    "lib/erlang/bin/start",
    "lib/erlang/erts-14.2.5.10/bin/erl",
    "lib/erlang/erts-14.2.5.10/bin/start",
]

BIN_SYMLINKS = [
    "bin/ct_run",
    "bin/dialyzer",
    "bin/epmd",
    "bin/erl",
    "bin/erlc",
    "bin/escript",
    "bin/run_erl",
    "bin/to_erl",
    "bin/typer",
]

LIB_OSMON_PRIV_BIN = [
    "lib/erlang/lib/os_mon-2.9.1/priv/bin/memsup",
    "lib/erlang/lib/os_mon-2.9.1/priv/bin/cpu_sup",
]

LIB_ERTS_BIN = [
    "lib/erlang/erts-14.2.5.10/bin/beam.smp",
    "lib/erlang/erts-14.2.5.10/bin/ct_run",
    "lib/erlang/erts-14.2.5.10/bin/dialyzer",
    "lib/erlang/erts-14.2.5.10/bin/dyn_erl",
    "lib/erlang/erts-14.2.5.10/bin/epmd",
    "lib/erlang/erts-14.2.5.10/bin/erl.src",
    "lib/erlang/erts-14.2.5.10/bin/erl_call",
    "lib/erlang/erts-14.2.5.10/bin/erl_child_setup",
    "lib/erlang/erts-14.2.5.10/bin/erlc",
    "lib/erlang/erts-14.2.5.10/bin/erlexec",
    "lib/erlang/erts-14.2.5.10/bin/escript",
    "lib/erlang/erts-14.2.5.10/bin/heart",
    "lib/erlang/erts-14.2.5.10/bin/inet_gethost",
    "lib/erlang/erts-14.2.5.10/bin/run_erl",
    "lib/erlang/erts-14.2.5.10/bin/start.src",
    "lib/erlang/erts-14.2.5.10/bin/start_erl.src",
    "lib/erlang/erts-14.2.5.10/bin/to_erl",
    "lib/erlang/erts-14.2.5.10/bin/typer",
    "lib/erlang/erts-14.2.5.10/bin/yielding_c_fun",
]

LIB_BIN = [
    "lib/erlang/bin/ct_run",
    "lib/erlang/bin/dialyzer",
    "lib/erlang/bin/erl_call",
    "lib/erlang/bin/erlc",
    "lib/erlang/bin/escript",
    "lib/erlang/bin/no_dot_erlang.boot",
    "lib/erlang/bin/run_erl",
    "lib/erlang/bin/start.boot",
    "lib/erlang/bin/start.script",
    "lib/erlang/bin/start_clean.boot",
    "lib/erlang/bin/start_erl",
    "lib/erlang/bin/start_sasl.boot",
    "lib/erlang/bin/to_erl",
    "lib/erlang/bin/typer",
]

exclude_from_filegroup(
    name = "erlang_purged",
    src = "@erlang//:gen_dir",
    excludes = [
        "Install",
        "examples",
        "misc",
        "include",
        "src",
    ] + OMD_ROOT_AWARE + LIB_OSMON_PRIV_BIN + LIB_ERTS_BIN + BIN_SYMLINKS,
)

genrule(
    name = "omd_root_aware",
    srcs = [
        "@erlang//:gen_dir",
    ],
    outs = OMD_ROOT_AWARE,
    cmd = """
        #!/bin/bash
        for F in $(OUTS); do
            cp -L $(execpath @erlang//:gen_dir)/{place_holder}/$${{F#$(RULEDIR)/}} $$F
            sed -i "s|{place_holder}|\\$${{OMD_ROOT}}|g" $$F
        done
    """.format(place_holder = PLACE_HOLDER),
)

genrule(
    name = "erlang_lib_osmon_priv_bin",
    srcs = [
        "@erlang//:gen_dir",
    ],
    outs = LIB_OSMON_PRIV_BIN,
    cmd = """
        #!/bin/bash
        for F in $(OUTS); do
            cp -L $(location @erlang//:gen_dir)/%s/$${F#$(RULEDIR)/} $$F
            chmod 750 $$F
        done
    """ % PLACE_HOLDER,
)

genrule(
    name = "erlang_lib_erts_bin",
    srcs = [
        "@erlang//:gen_dir",
    ],
    outs = LIB_ERTS_BIN,
    cmd = """
        #!/bin/bash
        for F in $(OUTS); do
            cp -L $(location @erlang//:gen_dir)/%s/$${F#$(RULEDIR)/} $$F
            chmod 750 $$F
        done
    """ % PLACE_HOLDER,
)

genrule(
    name = "erlang_lib_bin",
    srcs = [
        "@erlang//:gen_dir",
    ],
    outs = LIB_BIN,
    cmd = """
        #!/bin/bash
        for F in $(OUTS); do
            cp -L $(location @erlang//:gen_dir)/%s/$${F#$(RULEDIR)/} $$F
            chmod 750 $$F
        done
    """ % PLACE_HOLDER,
)

pkg_files(
    name = "omd_root_aware_pkg",
    srcs = [
        ":omd_root_aware",
    ],
    attributes = pkg_attributes(
        mode = "0755",
    ),
    strip_prefix = strip_prefix.from_pkg(""),
)

[
    pkg_mklink(
        name = bin + "_link",
        link_name = bin,
        target = "../lib/erlang/" + bin,
    )
    for bin in BIN_SYMLINKS
]

pkg_mklink(
    name = "epmd_lib_link",
    link_name = "lib/erlang/bin/epmd",
    target = "../erts-14.2.5.10/bin/epmd",
)

pkg_files(
    name = "lib_osmon_priv_bin_pkg",
    srcs = LIB_OSMON_PRIV_BIN,
    attributes = pkg_attributes(
        mode = "0755",
    ),
    prefix = "lib/erlang/lib/os_mon-2.9.1/priv/bin",
)

pkg_files(
    name = "lib_erts_bin_pkg",
    srcs = LIB_ERTS_BIN,
    attributes = pkg_attributes(
        mode = "0755",
    ),
    prefix = "lib/erlang/erts-14.2.5.10/bin",
)

pkg_files(
    name = "lib_bin_pkg",
    srcs = LIB_BIN,
    attributes = pkg_attributes(
        mode = "0755",
    ),
    prefix = "lib/erlang/bin",
)

filter_directory(
    name = "rest_stripped",
    src = ":erlang_purged",
    strip_prefix = strip_prefix.from_pkg(PLACE_HOLDER),
)

pkg_files(
    name = "rest",
    srcs = [
        ":rest_stripped",
    ],
    strip_prefix = strip_prefix.from_pkg("rest_stripped"),
)

pkg_tar(
    name = "erlang",
    srcs = [
        ":epmd_lib_link",
        ":lib_bin_pkg",
        ":lib_erts_bin_pkg",
        ":lib_osmon_priv_bin_pkg",
        ":omd_root_aware_pkg",
        ":rest",
    ] + [bin + "_link" for bin in BIN_SYMLINKS],
    visibility = ["//visibility:public"],
)
