load("@rules_foreign_cc//foreign_cc:defs.bzl", "configure_make")
load("@rules_pkg//pkg:mappings.bzl", "pkg_files")
load("@rules_pkg//pkg:tar.bzl", "pkg_tar")
load("//bazel/rules:patchelf.bzl", "set_runpath")
load("//omd/packages/Python:version.bzl", "PYTHON_MAJOR_DOT_MINOR")

configure_make(
    name = "mod_wsgi_build",
    args = ["-j4"],
    configure_in_place = True,
    configure_options = [
        "--with-python=$${EXT_BUILD_DEPS}/python/bin/python3",
        "--with-apxs=$$(command -v apxs2 || command -v apxs)",
    ],
    env = {
        "CFLAGS": "-I$${EXT_BUILD_DEPS}/python/include/python%s/" % PYTHON_MAJOR_DOT_MINOR,
        "LDFLAGS": "-L$${EXT_BUILD_DEPS}/python/lib -Wl,--strip-debug",
        "LD_LIBRARY_PATH": "$$EXT_BUILD_DEPS/python/lib/",
        "PKG_CONFIG_PATH": ":".join([
            "/usr/lib/pkgconfig",
            "/usr/lib64/pkgconfig",
            "/usr/lib/x86_64-linux-gnu/pkgconfig",
        ]),
    },
    lib_source = "@mod_wsgi//:all_srcs",
    linkopts = ["-Wl,--strip-all"],
    out_shared_libs = [
        "mod_wsgi.so",
    ],
    postfix_script = """
        cp src/server/.libs/mod_wsgi.so $$INSTALLDIR/lib
    """,
    targets = [""],
    deps = ["@python"],
)

filegroup(
    name = "mod_wsgi.so",
    srcs = [":mod_wsgi_build"],
    output_group = "mod_wsgi.so",
    visibility = ["//visibility:public"],
)

set_runpath(
    name = "mod_wsgi_runpath",
    srcs = [":mod_wsgi.so"],
    rpaths = ["${ORIGIN}/../../../lib"],
)

pkg_files(
    name = "lib_pkg",
    srcs = [
        ":mod_wsgi_runpath",
    ],
    prefix = "lib/apache/modules",
    tags = ["manual"],
)

pkg_files(
    name = "skel_pkg",
    srcs = [
        ":skel/etc/apache/conf.d/01_wsgi.conf",
    ],
    prefix = "skel/etc/apache/conf.d",
    tags = ["manual"],
)

pkg_tar(
    name = "mod_wsgi",
    srcs = [
        ":lib_pkg",
        ":skel_pkg",
    ],
    stamp = 1,
    tags = ["manual"],
    visibility = ["//omd:__pkg__"],
)
