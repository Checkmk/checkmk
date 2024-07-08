load("//:package_versions.bzl", "JAEGER_VERSION")

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
    outs = ["jaeger-all-in-one"],
    cmd = """
        target_path=$$(realpath $(RULEDIR)) ;\
	tar -xz \
	    --strip-components=1 \
	    -C $${target_path} \
	    -f $(SRCS) \
	    jaeger-%s-linux-amd64/jaeger-all-in-one
    """ % JAEGER_VERSION,
)

genrule(
    name = "hooks",
    srcs = [
        "@omd_packages//omd/packages/jaeger:TRACE_RECEIVE",
        "@omd_packages//omd/packages/jaeger:TRACE_RECEIVE_ADDRESS",
        "@omd_packages//omd/packages/jaeger:TRACE_RECEIVE_PORT",
    ],
    outs = [
        "lib/omd/hooks/TRACE_RECEIVE",
        "lib/omd/hooks/TRACE_RECEIVE_ADDRESS",
        "lib/omd/hooks/TRACE_RECEIVE_PORT",
    ],
    cmd = """
        mkdir -p $$(realpath $(RULEDIR))/lib/omd/hooks
        cp \
            $(execpath @omd_packages//omd/packages/jaeger:TRACE_RECEIVE) \
            $(execpath @omd_packages//omd/packages/jaeger:TRACE_RECEIVE_ADDRESS) \
            $(execpath @omd_packages//omd/packages/jaeger:TRACE_RECEIVE_PORT) \
            $$(realpath $(RULEDIR))/lib/omd/hooks/
    """,
)
