load("@bazel_tools//tools/build_defs/repo:http.bzl", "http_archive")
load("//:bazel_variables.bzl", "UPSTREAM_MIRROR_URL")

def heirloommailx_workspace():
    version_str = "12.5"
    filename = "heirloom-mailx_" + version_str + ".orig.tar.gz"
    http_archive(
        name = "heirloom-mailx",
        urls = [
            "https://ftp.nl.debian.org/debian-archive/debian/pool/main/h/heirloom-mailx/" + filename,
            UPSTREAM_MIRROR_URL + filename,
        ],
        sha256 = "015ba4209135867f37a0245d22235a392b8bbed956913286b887c2e2a9a421ad",
        build_file = "@omd_packages//omd/packages/heirloom-mailx:BUILD.heirloom-mailx.bazel",
        patches = [
            "//omd/packages/heirloom-mailx/patches:0001-nail-11.25-config.dif",
            "//omd/packages/heirloom-mailx/patches:0002-mailx-12.3-pager.dif",
            "//omd/packages/heirloom-mailx/patches:0003-mailx-12.5-lzw.dif",
            "//omd/packages/heirloom-mailx/patches:0004-mailx-12.5-fname-null.dif",
            "//omd/packages/heirloom-mailx/patches:0005-mailx-12.5-collect.dif",
            "//omd/packages/heirloom-mailx/patches:0006-mailx-12.5-usage.dif",
            "//omd/packages/heirloom-mailx/patches:0007-mailx-12.5-man-page-fixes.dif",
            "//omd/packages/heirloom-mailx/patches:0008-mailx-12.5-outof-Introduce-expandaddr-flag.dif",
            "//omd/packages/heirloom-mailx/patches:0009-mailx-12.5-fio.c-Unconditionally-require-wordexp-support.dif",
            "//omd/packages/heirloom-mailx/patches:0010-mailx-12.5-globname-Invoke-wordexp-with-WRDE_NOCMD-CVE-2004-277.dif",
            "//omd/packages/heirloom-mailx/patches:0011-mailx-12.5-unpack-Disable-option-processing-for-email-addresses.dif",
            "//omd/packages/heirloom-mailx/patches:0012-mailx-12.5-empty-from.dif",
            "//omd/packages/heirloom-mailx/patches:0013-mailx-12.5-nss-hostname-matching.dif",
            "//omd/packages/heirloom-mailx/patches:0014-mailx-12.5-encsplit.dif",
            "//omd/packages/heirloom-mailx/patches:0015-mailx-12.5-openssl.dif",
            "//omd/packages/heirloom-mailx/patches:0016-mailx-12.5-no-SSLv3.dif",
            "//omd/packages/heirloom-mailx/patches:0017-disable-ssl-and-kerberos.dif",
            "//omd/packages/heirloom-mailx/patches:0018-dont-install-etc-files.dif",
        ],
        patch_args = ["-p1"],
        patch_tool = "patch",
        strip_prefix = "heirloom-mailx-" + version_str,
    )
