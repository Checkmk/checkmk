load("@rules_foreign_cc//foreign_cc:defs.bzl", "configure_make")

filegroup(
    name = "all_srcs",
    srcs = glob(
        include = ["**/*"],
        exclude = ["*.bazel"],
    ),
)

# The build process with erlang has a strange handling of DESTDIR/INSTALL_PREFIX
# That's why we're installing it with a well-defined prefix which will be later patched to $OMD_ROOT in the Makefile
PLACE_HOLDER = "/replace-me-erlang"

configure_make(
    name = "erlang",
    args = ["-j4"],
    configure_in_place = True,
    # Mainly taken from rabbitmq's docker image:
    # https://github.com/rabbitmq/rabbitmq-server/blob/main/packaging/docker-image/Dockerfile
    configure_options = [
        "--prefix='%s'" % PLACE_HOLDER,
        "--disable-hipe",
        "--disable-sctp",
        "--disable-silent-rules",
        "--enable-builtin-zlib",
        "--enable-clock-gettime",
        "--enable-hybrid-heap",
        "--enable-kernel-poll",
        "--enable-smp-support",
        "--enable-threads",
        "--with-microstate-accounting=extra",
        "--with-ssl=$$EXT_BUILD_DEPS/openssl",
        "--without-common_test",
        "--without-debugger",
        "--without-dialyzer",
        "--without-diameter",
        "--without-edoc",
        "--without-erl_docgen",
        "--without-et",
        "--without-eunit",
        "--without-ftp",
        "--without-hipe",
        "--without-jinterface",
        "--without-megaco",
        "--without-observer",
        "--without-odbc",
        "--without-reltool",
        "--without-ssh",
        "--without-tftp",
        "--without-wx",
    ],
    copts = [
        "-Wl,--rpath,$ORIGIN_VAR/../lib",
        "-O2",
        "-g",
    ],
    env = {
        "ORIGIN_VAR": "\\\\$$\\$$ORIGIN",
    },
    install_prefix = "$INSTALLDIR",
    lib_source = ":all_srcs",
    out_bin_dir = "%s/bin/" % PLACE_HOLDER,
    out_binaries = [
        "ct_run",
        "dialyzer",
        "epmd",
        "erl",
        "erlc",
        "escript",
        "run_erl",
        "to_erl",
        "typer",
    ],
    out_data_dirs = [
        "%s/lib/" % PLACE_HOLDER,
    ],
    out_shared_libs = [
    ],
    out_static_libs = [
    ],
    postfix_script = """
        patchelf --force-rpath --set-rpath "\\$ORIGIN/../../../../../../lib" \
            $$INSTALLDIR$${place_holder}/lib/erlang/lib/crypto-5.4.2.1/priv/lib/crypto.so \
            $$INSTALLDIR$${place_holder}/lib/erlang/lib/crypto-5.4.2.1/priv/lib/otp_test_engine.so \
    """.format(place_holder = PLACE_HOLDER),
    visibility = ["//visibility:public"],
    deps = ["@openssl"],
)
