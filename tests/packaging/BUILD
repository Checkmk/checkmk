# Roots the Windows artifact signatures must chain to (Microsoft for Azure
# Artifact Signing and its timestamps).
filegroup(
    name = "signing_roots",
    srcs = glob(["certs/*.pem"]),
    visibility = ["//bazel/rules:__pkg__"],
)
