load("@bazel_tools//tools/build_defs/repo:http.bzl", "http_archive")
load("//:bazel_variables.bzl", "UPSTREAM_MIRROR_URL")

def heirloom_pkgtools(version_str, sha256):
    filename = "heirloom-pkgtools-" + version_str + ".tar.bz2"
    http_archive(
        name="heirloom-pkgtools",
        build_file="@omd_packages//packages/heirloom-pkgtools:BUILD.heirloom-pkgtools.bazel",
        strip_prefix="heirloom-pkgtools-" + version_str,
        patches = [
            "//packages/heirloom-pkgtools/patches:0000-set-linux-paths.dif",
            "//packages/heirloom-pkgtools/patches:0001-fix-invalid-open-call.dif",
            "//packages/heirloom-pkgtools/patches:0002-scriptvfy.l.dif",
            "//packages/heirloom-pkgtools/patches:0003-binpath.dif",
            "//packages/heirloom-pkgtools/patches:0004-compute_checksum-64bit.dif",
            "//packages/heirloom-pkgtools/patches:0005-compute_checksum-64bit.dif",
            "//packages/heirloom-pkgtools/patches:0006-sbinpath.dif",
            "//packages/heirloom-pkgtools/patches:0007-stropts.dif",
            "//packages/heirloom-pkgtools/patches:0008-fix-comilation-with-openssl-1.1.0.dif",
            "//packages/heirloom-pkgtools/patches:0008-libfl.dif",
            "//packages/heirloom-pkgtools/patches:0010-fix-missing-makedev.dif",
            "//packages/heirloom-pkgtools/patches:0011-add-fcommon.dif",
        ],
        patch_args = ["-p1"],
        patch_tool = "patch",
        urls=[
            "https://sourceforge.net/projects/heirloom/files/heirloom-pkgtools/" + version_str + "/" + filename,
            UPSTREAM_MIRROR_URL + filename,
        ],
        sha256=sha256,
    )
