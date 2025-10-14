load("@bazel_tools//tools/build_defs/repo:http.bzl", "http_archive")
load("//:bazel_variables.bzl", "UPSTREAM_MIRROR_URL")

def crypt_ssleay_workspace():
    version_str = "0.73_06"
    filename = "Crypt-SSLeay-" + version_str + ".tar.gz"
    http_archive(
        name = "Crypt-SSLeay",
        urls = [
            "https://www.cpan.org/modules/by-module/Net/NANIS/" + filename,
            UPSTREAM_MIRROR_URL + filename,
        ],
        sha256 = "f8ecca45c87eb91325992b13f0594f808e6f1bc4c3b9a7f141b9a838384d252c",
        build_file = "@omd_packages//omd/packages/perl-modules:BUILD.Crypt-SSLeay.bazel",
        patch_args = ["-p1"],
        patch_tool = "patch",
        strip_prefix = "Crypt-SSLeay-" + version_str,
    )
