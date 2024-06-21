load("//:package_versions.bzl", "REDFISH_MKP_VERSION")

genrule(
    name = "fetch_package",
    srcs = ["@redfish_mkp//file"],
    outs = ["redfish-" + REDFISH_MKP_VERSION + ".mkp"],
    cmd = """
        cp $(SRCS) $(OUTS)
    """,
)
