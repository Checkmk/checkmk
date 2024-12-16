load("@bazel_tools//tools/build_defs/repo:http.bzl", "http_archive")

def robotmk_workspace():
    version_str = "v3.0.0-alpha-15"
    http_archive(
        name = "robotmk",
        build_file = "//omd/packages/robotmk:BUILD.robotmk.bazel",
        urls = [
            "https://github.com/elabit/robotmk/releases/download/" + version_str + "/all_executables.zip",
        ],
        sha256 = "964a517f77439292b21bca8977683c4f702fd770e66133cfc5b20274460def0e",
    )
