load("@bazel_tools//tools/build_defs/repo:http.bzl", "http_archive")
load("//:bazel_variables.bzl", "UPSTREAM_MIRROR_URL")

def heirloom_pkgtools_workspace():
    version_str = "070227"
    filename = "heirloom-pkgtools-" + version_str + ".tar.bz2"
    http_archive(
        name = "heirloom-pkgtools",
        build_file = "@omd_packages//omd/packages/heirloom-pkgtools:BUILD.heirloom-pkgtools.bazel",
        strip_prefix = "heirloom-pkgtools-" + version_str,
        patches = [
            "//omd/packages/heirloom-pkgtools/patches:0000-set-linux-paths.dif",
            "//omd/packages/heirloom-pkgtools/patches:0001-fix-invalid-open-call.dif",
            "//omd/packages/heirloom-pkgtools/patches:0002-scriptvfy.l.dif",
            "//omd/packages/heirloom-pkgtools/patches:0003-binpath.dif",
            "//omd/packages/heirloom-pkgtools/patches:0004-compute_checksum-64bit.dif",
            "//omd/packages/heirloom-pkgtools/patches:0005-compute_checksum-64bit.dif",
            "//omd/packages/heirloom-pkgtools/patches:0006-sbinpath.dif",
            "//omd/packages/heirloom-pkgtools/patches:0007-stropts.dif",
            "//omd/packages/heirloom-pkgtools/patches:0008-fix-comilation-with-openssl-1.1.0.dif",
            "//omd/packages/heirloom-pkgtools/patches:0008-libfl.dif",
            "//omd/packages/heirloom-pkgtools/patches:0010-fix-missing-makedev.dif",
            "//omd/packages/heirloom-pkgtools/patches:0011-add-fcommon.dif",
        ],
        patch_args = ["-p1"],
        patch_tool = "patch",
        urls = [
            "https://sourceforge.net/projects/heirloom/files/heirloom-pkgtools/" + version_str + "/" + filename,
            UPSTREAM_MIRROR_URL + filename,
        ],
        sha256 = "aa94d33550847d57c62138cabd0f742d4af2f14aa2bfb9e9d4a9427bf498e6cc",
    )
