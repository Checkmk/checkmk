load("@bazel_tools//tools/build_defs/repo:http.bzl", "http_archive")
load("//:bazel_variables.bzl", "UPSTREAM_MIRROR_URL")

def protobuf(version_str, sha256):
    filename = "protobuf-python-" + version_str + ".tar.gz"
    http_archive(
        name = "protobuf",
        build_file = "@omd_packages//omd/packages/protobuf:BUILD.protobuf.bazel",
        strip_prefix = "protobuf-" + version_str,
        urls = [
            "https://github.com/protocolbuffers/protobuf/releases/download/v" + version_str + "/" + filename,
            UPSTREAM_MIRROR_URL + filename,
        ],
        patches = [
            "//omd/packages/protobuf/patches:00-unused-parameters.dif",
            "//omd/packages/protobuf/patches:01-tweaks-for-iwyu.dif",
            "//omd/packages/protobuf/patches:02-Fix-build-with-Python-3.11.dif",
            "//omd/packages/protobuf/patches:03-noreturn-fix.dif",
            "//omd/packages/protobuf/patches:04-linking-error.dif",
        ],
        patch_args = ["-p1"],
        patch_tool = "patch",
        sha256 = sha256,
    )
