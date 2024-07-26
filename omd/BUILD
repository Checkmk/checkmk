# List of Packages that are installed into intermediate install.
# This should be extended to all packages once there is a target
# to create dest, since intermediate install can be removed at
# that point.
PACKAGES_EXT = [
    "freetds",
    "net-snmp",
    "openssl",
    "python",
    "rrdtool",
]

PACKAGES_EXT_LABEL = ["@%s//:%s" % (p, p) for p in PACKAGES_EXT]

PACKAGES_INT = [
    "//omd/packages/perl-modules:perl-modules.tar",
    "//omd/packages/python3-modules:python3-modules.tar",
]

genrule(
    name = "intermediate_install",
    srcs = PACKAGES_EXT_LABEL + PACKAGES_INT,
    outs = ["intermediate_install.tar.gz"],
    cmd = """
        set -x
        echo $$PWD
        ls -lah
        mkdir intermediate_install
        for F in $(SRCS); do
            if [[ "$$F" == *.tar ]];
            then
                tar -xf $$F -C intermediate_install
            elif [[ $$(ls $$F/*.tar) == *.tar ]]
            then
                tar -xf $$F/*.tar -C intermediate_install
            fi
        done

        # package created files into archive
        tar cf $@ intermediate_install
    """,
)
