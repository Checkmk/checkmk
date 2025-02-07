JAEGER_VERSION = "2.3.0"

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
