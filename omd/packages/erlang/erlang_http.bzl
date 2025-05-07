load("@bazel_tools//tools/build_defs/repo:http.bzl", "http_archive")
load("//:bazel_variables.bzl", "UPSTREAM_MIRROR_URL")

def erlang_workspace():
    filename = "otp_src_26.2.5.2.tar.gz"
    http_archive(
        name = "erlang",
        urls = [
            UPSTREAM_MIRROR_URL + filename,
            "https://github.com/erlang/otp/releases/download/OTP-26.2.5.2/" + filename,
        ],
        sha256 = "e49708cf1f602863e394869af48df4abcb39e3633b96cb4babde3ee7aa724872",
        build_file = "@omd_packages//omd/packages/erlang:BUILD",
        strip_prefix = "otp_src_26.2.5.2",
    )
