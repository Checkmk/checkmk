load("@bazel_tools//tools/build_defs/repo:http.bzl", "http_archive")
load("//:bazel_variables.bzl", "UPSTREAM_MIRROR_URL")

def crypt_ssleay(version_str, sha256):
    filename = "Crypt-SSLeay-" + version_str + ".tar.gz"
    http_archive(
        name = "Crypt-SSLeay",
        urls = [
            "https://www.cpan.org/modules/by-module/Net/NANIS/" + filename,
            UPSTREAM_MIRROR_URL + filename,
        ],
        sha256 = sha256,
        build_file = "@omd_packages//omd/packages/perl-modules:BUILD.Crypt-SSLeay.bazel",
        patches = [
            "//omd/packages/perl-modules/patches:Crypt-SSLeay-0.72-do-not-use-SSLv2_client_method-with-new-openssl.dif",
        ],
        patch_args = ["-p1"],
        patch_tool = "patch",
        strip_prefix = "Crypt-SSLeay-" + version_str,
    )
