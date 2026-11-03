#!groovy

/// file: relay-msi-linux.groovy
///
/// Builds the relay's Windows installer MSI on Linux and signs it via Azure
/// Artifact Signing, the counterpart of relay-msi.groovy on the Windows nodes.
/// The package build still takes the MSI from relay-msi.

void main() {
    check_job_parameters([
        ["VERSION", true],
        ["EDITION", true],
        ["DISABLE_CACHE", false],
    ]);
    def disable_cache = params.DISABLE_CACHE;

    def windows = load("${checkout_dir}/buildscripts/scripts/utils/windows.groovy");
    def test_jenkins_helper = load("${checkout_dir}/buildscripts/scripts/utils/test_helper.groovy");
    def versioning = load("${checkout_dir}/buildscripts/scripts/utils/versioning.groovy");
    def safe_branch_name = versioning.safe_branch_name();
    def branch_version = versioning.get_branch_version(checkout_dir);
    def cmk_version = versioning.strip_rc_number_from_version(
        versioning.get_cmk_version(safe_branch_name, branch_version, params.VERSION)
    );

    def edition = params.EDITION;
    def allowed_editions = ["cloud", "ultimate", "ultimatemt"];
    if (!(edition in allowed_editions)) {
        error("Edition '${edition}' is not supported for the relay MSI build. Allowed editions: ${allowed_editions}.");
    }

    def bazel_args = "--cmk_edition=${edition} --cmk_version=${cmk_version}";
    def msi_target = "//non-free/packages/cmk-relay-engine/windows-installer:msi";
    def msi_test_target = "//non-free/packages/cmk-relay-engine/windows-installer:msi_test";

    dir("${checkout_dir}") {
        def container_name = "testing-ubuntu-2204-checkmk-${safe_branch_name.replace('.', '-')}";
        container(container_name) {
            if (disable_cache) {
                sh("rm -rf remote.bazelrc");
            }

            stage("Build relay MSI") {
                sh(
                    """
                    set -euo pipefail
                    bazel build ${bazel_args} ${msi_target}
                    mkdir -p artefacts
                    cp -f \$(bazel cquery ${bazel_args} --output=files ${msi_target}) artefacts/
                    """
                );
            }

            stage("Test relay MSI") {
                try {
                    sh("bazel test ${bazel_args} ${msi_test_target}");
                } finally {
                    sh(
                        """
                        BAZEL_TEST_LOGS_DEST=results buildscripts/scripts/bazel_test_post_archive_xunit.sh || :
                        """
                    );
                }
            }

            // After the test (it checks the bazel output, not artefacts/).
            stage("Sign relay MSI") {
                windows.sign_with_azure(safe_branch_name, bazel_args, ["artefacts/CheckmkRelayInstaller.msi"]);
            }
        }

        stage("Archive MSI") {
            dir("artefacts") {
                archiveArtifacts(
                    artifacts: "CheckmkRelayInstaller.msi",
                    fingerprint: true,
                );
            }
        }

        stage("Archive test results") {
            archiveArtifacts(
                allowEmptyArchive: true,
                artifacts: "results/**/test.xml",
                fingerprint: true,
            );
            test_jenkins_helper.analyse_issues("JUNIT", "results/**/test.xml");
        }
    }
}

return this;
