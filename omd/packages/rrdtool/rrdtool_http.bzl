load("@bazel_tools//tools/build_defs/repo:http.bzl", "http_archive")
load("//:bazel_variables.bzl", "UPSTREAM_MIRROR_URL")

def rrdtool(version_str, sha256):
    filename = "rrdtool-" + version_str + ".tar.gz"
    http_archive(
        name = "rrdtool",
        build_file = "@omd_packages//omd/packages/rrdtool:BUILD.rrdtool.bazel",
        strip_prefix = "rrdtool-" + version_str,
        urls = [
            "https://src.fedoraproject.org/repo/pkgs/rrdtool/" +
            filename +
            "/sha512/453230efc68aeb4a12842d20a9d246ba478a79c2f6bfd9693a91837c1c1136abe8af177be64fe29aa40bf84ccfce7f2f15296aefe095e89b8b62aef5a7623e29/" +
            filename,
            UPSTREAM_MIRROR_URL + filename,
        ],
        patches = [
            "//omd/packages/rrdtool/patches:0001-xff_field_missing_from_rrdinfo.dif",
            "//omd/packages/rrdtool/patches:0003-cli-xport-consistency.dif",
            "//omd/packages/rrdtool/patches:0004-fix-error-formatting.dif",
        ],
        patch_args = ["-p1"],
        patch_tool = "patch",
        sha256 = sha256,
    )
