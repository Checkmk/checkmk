"""The pinned Windows Server Core test image, and the size of the VMs run from it.

Built by `bazel run --config=test-vm //agents/wnx/test-vm:build-core` (the
winagt-build-test-vm-image Jenkins job) and published to Nexus upstream-archives under
a versioned name. Bump all three fields together with the values upload-image.sh
prints. The Eval licence of the image ends at `expires`: the VM is not started from the
day before (qemu_windows/state.py), and a new image is due before then (the Eval runs
180 days from the build).
"""

WINDOWS_TEST_IMAGE = struct(
    file = "win2022-core-2026-10-24-1800.qcow2",
    sha256 = "83812aa3261b395fc0958c741f36f829f2ae7133326c1bd85902640b2858624e",
    expires = "2027-04-22",
)

# The VM the image runs in: the image build, the saved state
# (windows_vm_state.bzl) and every VM resumed from it. A state only resumes
# with the size it was saved with; the state action's command line holds the
# size, so changing it here rebuilds the state.
WINDOWS_TEST_VM = struct(
    cpus = 4,
    memory_mib = 4096,
    # What Bazel reserves per running VM, in its MB: the guest's RAM plus
    # QEMU's own.
    claim_mb = 4700,
)
