load("@bazel_tools//tools/build_defs/repo:http.bzl", "http_archive")

def robotmk_workspace():
    version_str = "v3.0.1"
    http_archive(
        name = "robotmk",
        build_file = "//omd/packages/robotmk:BUILD.robotmk.bazel",
        urls = [
            "https://github.com/elabit/robotmk/releases/download/" + version_str + "/all_executables.zip",
        ],
        sha256 = "49d23d13d95db555799b180c3da3bd002bb4c197c336b088c4cecbcce3476e50",
    )
