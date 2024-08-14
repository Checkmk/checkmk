filegroup(
    name = "all_srcs",
    srcs = glob(["**"]),
)

genrule(
    name = "build",
    srcs = [
        ":all_srcs",
    ],
    outs = [
        "rabbitmq.tar.gz",
    ],
    cmd = """
        tar --dereference -czvf $$(realpath $(RULEDIR))/rabbitmq.tar.gz  \
            -C external \
            --exclude=LICENSE* \
            --exclude=INSTALL* \
            --exclude=BUILD* \
            --exclude=WORKSPACE* \
            rabbitmq/;
    """,
    visibility = ["//visibility:public"],
)
