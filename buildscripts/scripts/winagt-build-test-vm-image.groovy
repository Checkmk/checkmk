#!groovy

/// file: winagt-build-test-vm-image.groovy

/// Builds the Windows Server 2022 Core test image the *-qemu test tiers run
/// in (agents/wnx/test-vm) and publishes it to the Nexus
/// upstream-archives mirror under a versioned name. The image's Eval licence
/// runs 180 days from the build, so this runs at least every few months; the
/// three fields the upload prints then go into agents/wnx/test-vm/image.bzl.
///
/// Runs in the master-standard-kvm pod template (/dev/kvm through the
/// devices.kubevirt.io/kvm resource) and needs about 30 GB of free disk;
/// takes 45 to 60 minutes: about 40 for the build, the rest for the media
/// download and the upload.
///
/// Credentials:
///     nexus -> NEXUS_USERNAME / NEXUS_PASSWORD

void main() {
    def name = "win2022-core-${new Date().format('yyyy-MM-dd-HHmm', TimeZone.getTimeZone('UTC'))}.qcow2";

    dir("${checkout_dir}") {
        // The job's pod template (master-standard-kvm) gives this container
        // /dev/kvm.
        inside_container() {
            // Before the half-hour build: a stale credential fails here.
            stage("Check the Nexus credentials") {
                withNexusCredentials {
                    sh("agents/wnx/test-vm/upload-image.sh --check ${name}");
                }
            }
            stage("Build the image") {
                sh("""
                    set -euo pipefail
                    rm -rf test-vm-out
                    mkdir -p test-vm-out
                    bazel run --config=test-vm //agents/wnx/test-vm:build-core -- --out \${PWD}/test-vm-out/${name}
                """);
            }
            stage("Publish the image") {
                withNexusCredentials {
                    sh("agents/wnx/test-vm/upload-image.sh test-vm-out/${name} ${name}");
                }
            }
        }
    }
}

return this;
