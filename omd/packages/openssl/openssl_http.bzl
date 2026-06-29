load("@bazel_tools//tools/build_defs/repo:http.bzl", "http_archive")
load("//:bazel_variables.bzl", "UPSTREAM_MIRROR_URL")

def openssl_workspace():
    version_str = "3.0.21"
    filename = "openssl-" + version_str + ".tar.gz"
    http_archive(
        name = "openssl",
        urls = [
            "https://github.com/openssl/openssl/releases/download/openssl-" + version_str + "/" + filename,
            UPSTREAM_MIRROR_URL + filename,
        ],
        sha256 = "617e29af8e421f46649484a4937e48c685e47f46488167c982f88bc4ec1d522f",
        build_file = "@omd_packages//omd/packages/openssl:BUILD.openssl.bazel",
        strip_prefix = "openssl-" + version_str,
        patch_args = ["-p1"],
        patch_tool = "patch",
        patches = [
            "@omd_packages//omd/packages/openssl/patches:0001-strip-bazel-paths-from-buildinf.patch",
        ],
    )
