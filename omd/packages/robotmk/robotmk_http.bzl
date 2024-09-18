load("@bazel_tools//tools/build_defs/repo:http.bzl", "http_archive")

def robotmk_workspace():
    version_str = "v3.0.0-alpha-7"
    http_archive(
        name = "robotmk",
        build_file = "//omd/packages/robotmk:BUILD.robotmk.bazel",
        urls = [
            "https://github.com/elabit/robotmk/releases/download/" + version_str + "/executables.zip",
        ],
        sha256 = "78d1b5bde14b2f8421181b5ef1733e205a4f13b1229b26924861764f61175401",
    )
