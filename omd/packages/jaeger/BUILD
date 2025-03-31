load("@rules_pkg//pkg:mappings.bzl", "pkg_attributes", "pkg_files", "pkg_mklink", "strip_prefix")
load("@rules_pkg//pkg:tar.bzl", "pkg_tar")

JAEGER_VERSION = "2.3.0"

exports_files(["skel.permissions"])

genrule(
    name = "fetch_package",
    srcs = ["@jaeger//file"],
    outs = ["jaeger-" + JAEGER_VERSION + "-linux-amd64.tar.gz"],
    cmd = """
        cp $(SRCS) $(OUTS)
    """,
)

genrule(
    name = "extract_binary",
    srcs = [":fetch_package"],
    outs = ["jaeger"],
    cmd = """
        target_path=$$(realpath $(RULEDIR)) ;\
	tar -xz \
	    --strip-components=1 \
	    -C $${target_path} \
	    -f $(SRCS) \
	    jaeger-%s-linux-amd64/jaeger
    """ % JAEGER_VERSION,
)

genrule(
    name = "hooks",
    srcs = [
        "@omd_packages//omd/packages/jaeger:TRACE_RECEIVE",
        "@omd_packages//omd/packages/jaeger:TRACE_RECEIVE_ADDRESS",
        "@omd_packages//omd/packages/jaeger:TRACE_RECEIVE_PORT",
        "@omd_packages//omd/packages/jaeger:TRACE_JAEGER_ADMIN_PORT",
        "@omd_packages//omd/packages/jaeger:TRACE_JAEGER_UI_PORT",
    ],
    outs = [
        "lib/omd/hooks/TRACE_RECEIVE",
        "lib/omd/hooks/TRACE_RECEIVE_ADDRESS",
        "lib/omd/hooks/TRACE_RECEIVE_PORT",
        "lib/omd/hooks/TRACE_JAEGER_ADMIN_PORT",
        "lib/omd/hooks/TRACE_JAEGER_UI_PORT",
    ],
    cmd = """
        mkdir -p $$(realpath $(RULEDIR))/lib/omd/hooks
        cp \
            $(execpath @omd_packages//omd/packages/jaeger:TRACE_RECEIVE) \
            $(execpath @omd_packages//omd/packages/jaeger:TRACE_RECEIVE_ADDRESS) \
            $(execpath @omd_packages//omd/packages/jaeger:TRACE_RECEIVE_PORT) \
            $(execpath @omd_packages//omd/packages/jaeger:TRACE_JAEGER_ADMIN_PORT) \
            $(execpath @omd_packages//omd/packages/jaeger:TRACE_JAEGER_UI_PORT) \
            $$(realpath $(RULEDIR))/lib/omd/hooks/
    """,
)

pkg_files(
    name = "jaeger_bin_pkg",
    srcs = [":jaeger"],
    attributes = pkg_attributes(
        mode = "0755",
    ),
    prefix = "bin",
)

pkg_files(
    name = "jaeger_lib_hooks_pkg",
    srcs = [
        ":lib/omd/hooks/TRACE_JAEGER_ADMIN_PORT",
        ":lib/omd/hooks/TRACE_JAEGER_UI_PORT",
        ":lib/omd/hooks/TRACE_RECEIVE",
        ":lib/omd/hooks/TRACE_RECEIVE_ADDRESS",
        ":lib/omd/hooks/TRACE_RECEIVE_PORT",
    ],
    attributes = pkg_attributes(
        mode = "0755",
    ),
    strip_prefix = strip_prefix.from_pkg(""),
)

pkg_files(
    name = "skel",
    srcs = [
        "skel/etc/jaeger/config.yaml",
        "skel/etc/logrotate.d/jaeger",
    ],
    strip_prefix = strip_prefix.from_pkg(""),
)

pkg_files(
    name = "skel_755",
    srcs = [
        "skel/etc/init.d/jaeger",
    ],
    attributes = pkg_attributes(
        mode = "0755",
    ),
    strip_prefix = strip_prefix.from_pkg(""),
)

pkg_mklink(
    name = "08-jaeger",
    link_name = "skel/etc/rc.d/08-jaeger",
    target = "../init.d/jaeger",
)

pkg_tar(
    name = "pkg_tar",
    srcs = [
        ":08-jaeger",
        ":jaeger_bin_pkg",
        ":jaeger_lib_hooks_pkg",
        ":skel",
        ":skel_755",
    ],
    visibility = ["//omd:__pkg__"],
)
