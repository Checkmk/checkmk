REDFISH_MKP_VERSION = "2.3.38"

genrule(
    name = "fetch_package",
    srcs = ["@redfish_mkp//file"],
    outs = ["redfish-" + REDFISH_MKP_VERSION + ".mkp"],
    cmd = """
        cp $(SRCS) $(OUTS)
    """,
)
