load("@bazel_tools//tools/build_defs/repo:http.bzl", "http_archive")
load("//:bazel_variables.bzl", "UPSTREAM_MIRROR_URL")

def crypt_ssleay_workspace():
    version_str = "0.72"
    filename = "Crypt-SSLeay-" + version_str + ".tar.gz"
    http_archive(
        name = "Crypt-SSLeay",
        urls = [
            "https://www.cpan.org/modules/by-module/Net/NANIS/" + filename,
            UPSTREAM_MIRROR_URL + filename,
        ],
        sha256 = "f5d34f813677829857cf8a0458623db45b4d9c2311daaebe446f9e01afa9ffe8",
        build_file = "@omd_packages//omd/packages/perl-modules:BUILD.Crypt-SSLeay.bazel",
        patches = [
            "//omd/packages/perl-modules/patches:Crypt-SSLeay-0.72-do-not-use-SSLv2_client_method-with-new-openssl.dif",
        ],
        patch_args = ["-p1"],
        patch_tool = "patch",
        strip_prefix = "Crypt-SSLeay-" + version_str,
    )
