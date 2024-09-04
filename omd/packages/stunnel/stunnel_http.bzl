load("@bazel_tools//tools/build_defs/repo:http.bzl", "http_archive")
load("//:bazel_variables.bzl", "UPSTREAM_MIRROR_URL")

def stunnel_workspace():
    version_str = "5.63"
    filename = "stunnel-" + version_str + ".tar.gz"
    http_archive(
        name = "stunnel",
        build_file = "@omd_packages//omd/packages/stunnel:BUILD.stunnel.bazel",
        strip_prefix = "stunnel-" + version_str,
        urls = [
            "https://ftp.nluug.nl/pub/networking/stunnel/archive/5.x/" + filename,
            UPSTREAM_MIRROR_URL + filename,
        ],
        sha256 = "c74c4e15144a3ae34b8b890bb31c909207301490bd1e51bfaaa5ffeb0a994617",
    )
