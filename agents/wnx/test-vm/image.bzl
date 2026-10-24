"""The pinned Windows Server Core test image.

Built by `bazel run --config=test-vm //agents/wnx/test-vm:build-core` (the
winagt-build-test-vm-image Jenkins job) and published to Nexus upstream-archives under
a versioned name. Bump all three fields together with the values upload-image.sh
prints. The Eval licence of the image ends at `expires`, and a new image is due before
then (the Eval runs 180 days from the build).
"""

WINDOWS_TEST_IMAGE = struct(
    file = "win2022-core-2026-10-24-1800.qcow2",
    sha256 = "83812aa3261b395fc0958c741f36f829f2ae7133326c1bd85902640b2858624e",
    expires = "2027-04-22",
)
