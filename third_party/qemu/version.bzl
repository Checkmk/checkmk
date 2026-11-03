"""The pinned static QEMU build (third_party/qemu).

Bumped together with sources.txt (and create-archive's REVISION). build_qemu.sh
refuses to publish an archive whose sha256 differs from this pin: the recipe is
reproducible, so the pin is computed from a local build and committed first.
"""

QEMU_ARCHIVE = struct(
    name = "qemu-11.1.1-r6-linux-x86_64",
    sha256 = "f81b0ad0b5cd99e29957d1ef2c508a604fb3f571eba7540a7e79dfd64c963afc",
)
