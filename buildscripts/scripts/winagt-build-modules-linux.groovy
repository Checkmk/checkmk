#!groovy

/// file: winagt-build-modules-linux.groovy
///
/// Builds python-3.cab (the Windows agent's bundled Python runtime) on a
/// Linux build node via the Bazel rule //agents/modules/windows:python_3_cab,
/// and archives it for the Windows integration test (which runs on a Windows
/// node and can't build the Linux-only rule itself).
///
/// The deb/rpm/cma package build no longer consumes this job's artifact; it
/// builds the cab directly in its own Bazel graph (see agents/windows/BUILD).
///
/// The build is hermetic: the win_amd64 wheel closure is sha256-pinned and
/// fetched at Bazel's fetch phase (see agents/modules/windows/python_cab.bzl),
/// so no Nexus mirror / PIP_EXTRA_INDEX_URL is needed.

void main() {
    def versioning = load("${checkout_dir}/buildscripts/scripts/utils/versioning.groovy");
    def safe_branch_name = versioning.safe_branch_name();

    check_job_parameters([
        ["DISABLE_CACHE", false],
    ]);
    def disable_cache = params.DISABLE_CACHE;

    dir("${checkout_dir}") {
        stage("Build python-3.cab") {
            // The cab rule is hermetic, so it hits the same remote-cache entries the deb/rpm/cma
            // package build populates it does not need to be built in the distro build image.
            def container_name = "testing-ubuntu-2204-checkmk-${safe_branch_name.replace('.', '-')}";
            container(container_name) {
                if (disable_cache) {
                    sh("rm -rf remote.bazelrc");
                }
                sh(
                    """
                    set -euo pipefail
                    bazel build //agents/modules/windows:python_3_cab
                    mkdir -p agents/modules/windows/artefacts
                    cp -f bazel-bin/agents/modules/windows/python_3_cab.cab \\
                          agents/modules/windows/artefacts/python-3.cab
                    """
                );
            }
        }

        stage("Archive python-3.cab") {
            dir("agents/modules/windows/artefacts") {
                archiveArtifacts(
                    artifacts: 'python-3.cab',
                    fingerprint: true,
                );
            }
        }
    }
}

return this;
