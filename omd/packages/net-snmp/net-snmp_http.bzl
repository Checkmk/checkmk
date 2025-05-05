load("@bazel_tools//tools/build_defs/repo:http.bzl", "http_archive")
load("//:bazel_variables.bzl", "UPSTREAM_MIRROR_URL")

def netsnmp_workspace():
    version_str = "5.9.1"
    filename = "net-snmp-" + version_str + ".zip"
    http_archive(
        name = "net-snmp",
        build_file = "@omd_packages//omd/packages/net-snmp:BUILD.net-snmp.bazel",
        strip_prefix = "net-snmp-" + version_str,
        urls = [
            UPSTREAM_MIRROR_URL + filename,
            "https://deac-riga.dl.sourceforge.net/project/net-snmp/net-snmp/" + version_str + "/" + filename,
        ],
        patches = [
            "//omd/packages/net-snmp/patches:0001-remove-distutils.dif",
            "//omd/packages/net-snmp/patches:0002-We-use-a-C-extension-so-we-are-better-not-zip_safe.dif",
            "//omd/packages/net-snmp/patches:0003-Added-handling-of-opaque-floats.dif",
            "//omd/packages/net-snmp/patches:0004-Fixed-copy-n-paste-error-regarding-the-context-engine-.dif",
            "//omd/packages/net-snmp/patches:0005-Fixed-__snprint_value-s-return-value.dif",
            "//omd/packages/net-snmp/patches:0006-Added-missing-initialization-of-Version-attribute.dif",
            "//omd/packages/net-snmp/patches:0007-Fixed-reference-counting-for-netsnmp-module.dif",
            "//omd/packages/net-snmp/patches:0008-Fixed-segfaults-in-netsnmp_-walk-getbulk-when-a-varbin.dif",
            "//omd/packages/net-snmp/patches:0009-Added-workaround-for-duplicate-engine-IDs.dif",
            "//omd/packages/net-snmp/patches:0010-Emulate-Cc-behavior-in-netsnmp_walk.dif",
            "//omd/packages/net-snmp/patches:0011-Handle-responses-with-invalid-variables-differently.dif",
            "//omd/packages/net-snmp/patches:0012-Ensure-correct-openssl-version.dif",
            "//omd/packages/net-snmp/patches:0013-fix-possible-TypeError-AttributeError-in-__del__.dif",
            "//omd/packages/net-snmp/patches:0014-fix-curses-detection.dif",
            "//omd/packages/net-snmp/patches:0015-python3-api.dif",
            "//omd/packages/net-snmp/patches:0016-Python-Fix-snmpwalk-with-UseNumeric-1.dif",
            "//omd/packages/net-snmp/patches:0017-no-fallthrough.dif",
            "//omd/packages/net-snmp/patches:0018-update-user-information-for-python.dif",
        ],
        patch_args = ["-p1"],
        patch_tool = "patch",
        sha256 = "75b59d67e871aaaa31c8cef89ba7d06972782b97736b7e8c3399f36b50a8816f",
    )
