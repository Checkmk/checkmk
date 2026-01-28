load("@bazel_tools//tools/build_defs/repo:http.bzl", "http_archive")

def robotmk_workspace():
    version_str = "v3.0.2"
    http_archive(
        name = "robotmk",
        build_file = "//omd/packages/robotmk:BUILD.robotmk.bazel",
        urls = [
            "https://github.com/elabit/robotmk/releases/download/" + version_str + "/all_executables.zip",
        ],
        sha256 = "0a479530d7299044eed35c5f22aa5cb4f5f983aacbc928808851b2ba998c2e7e",
    )
