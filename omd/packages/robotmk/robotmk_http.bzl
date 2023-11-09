load("@bazel_tools//tools/build_defs/repo:http.bzl", "http_archive")

def robotmk(version_str, sha256):
    http_archive(
        name = "robotmk",
        build_file = "//omd/packages/robotmk:BUILD.robotmk",
        # TODO TBC: switch to official release
        url = "https://github.com/SoloJacobs/robotmk/releases/download/" + version_str + "/executables.zip",
        sha256 = sha256,
    )
