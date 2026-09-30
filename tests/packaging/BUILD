# Roots the Windows artifact signatures must chain to (Sectigo for the YubiKey
# path, Microsoft for Azure Artifact Signing and its timestamps).
filegroup(
    name = "signing_roots",
    srcs = glob(["certs/*.pem"]),
    visibility = ["//agents/wnx/scripts:__pkg__"],
)
