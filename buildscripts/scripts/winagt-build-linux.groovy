#!groovy

/// file: winagt-build-linux.groovy
///
/// Builds the Windows agent artifacts that can be produced on Linux.

void main() {
    check_job_parameters([
        ["VERSION", true],
        ["DISABLE_CACHE", false],
    ]);
    def disable_cache = params.DISABLE_CACHE;

    def test_jenkins_helper = load("${checkout_dir}/buildscripts/scripts/utils/test_helper.groovy");
    def versioning = load("${checkout_dir}/buildscripts/scripts/utils/versioning.groovy");
    def safe_branch_name = versioning.safe_branch_name();
    def branch_version = versioning.get_branch_version(checkout_dir);
    def cmk_version = versioning.strip_rc_number_from_version(
        versioning.get_cmk_version(safe_branch_name, branch_version, params.VERSION)
    );

    // Everything derives from the label (artifact via cquery, -static-crt
    // test), so adding a binary here wires up the whole job.
    def exe_targets = [
        "//packages/cmk-agent-ctl:cmk-agent-ctl-windows",
        "//packages/mk-sql:mk-sql-windows",
        "//packages/mk-oracle:mk-oracle-windows",
        "//agents/wnx/extensions/robotmk_ext:robotmk_ext-windows",
    ];
    // Built and archived like the binaries, but there is no -static-crt tier
    // for an MSI to check.
    def targets = exe_targets + ["//agents/wnx:check_mk_agent_msi"];
    // The Wine unit-test tiers of the targets above (a separate list:
    // not every artifact has one).
    def wine_test_targets = [
        "//packages/cmk-agent-ctl:cmk-agent-ctl-tests-wine",
        "//packages/mk-sql:mk-sql-tests-wine",
        "//packages/mk-oracle:mk-oracle-tests-wine",
        "//agents/wnx:watest-wine",
    ];
    // The toolchain's own contract test.
    def toolchain_test_targets = [
        "//bazel/toolchains/cc/clang/xwin/tests:tests",
    ];
    def target_args = targets.join(" ");
    def crt_test_args = exe_targets.collect { it + "-static-crt" }.join(" ");
    // Fail the build but keep going, so the test results below still get
    // collected and published.
    def fail_and_continue = [buildResult: 'FAILURE', stageResult: 'FAILURE'];

    dir("${checkout_dir}") {
        def container_name = "testing-ubuntu-2204-checkmk-${safe_branch_name.replace('.', '-')}";
        container(container_name) {
            if (disable_cache) {
                sh("rm -rf remote.bazelrc");
            }

            stage("Build windows binaries") {
                sh(
                    """
                    set -euo pipefail
                    bazel build --cmk_version=${cmk_version} ${target_args}
                    mkdir -p artefacts
                    """
                );
                // The outputs already carry the Windows-node job's artifact
                // names (binary_name on the targets).
                targets.each { target ->
                    sh("cp -f \$(bazel cquery --cmk_version=${cmk_version} --output=files ${target}) artefacts/");
                }
            }

            stage("Check toolchain argument contract") {
                catchError(fail_and_continue) {
                    sh(
                        """
                        set -euo pipefail
                        bazel test --cmk_version=${cmk_version} ${toolchain_test_targets.join(" ")}
                        """
                    );
                }
            }

            stage("Run unit tests under Wine") {
                catchError(fail_and_continue) {
                    sh(
                        """
                        set -euo pipefail
                        bazel test --cmk_version=${cmk_version} ${wine_test_targets.join(" ")}
                        """
                    );
                }
            }

            stage("Check static CRT") {
                catchError(fail_and_continue) {
                    sh(
                        """
                        set -euo pipefail
                        bazel test --cmk_version=${cmk_version} ${crt_test_args}
                        """
                    );
                }
            }

            stage("Collect test results") {
                collect_test_results();
            }

            // After the tests (they use the bazel outputs, not artefacts/),
            // so a signing outage still fails the job but keeps the test
            // feedback.
            stage("Sign windows binaries") {
                sign_windows_binaries(safe_branch_name, cmk_version, "artefacts");
            }
        }

        stage("Archive binaries") {
            dir("artefacts") {
                archiveArtifacts(
                    artifacts: "*.exe,*.msi",
                    fingerprint: true,
                );
            }
        }

        stage("Archive test results") {
            archiveArtifacts(
                allowEmptyArchive: false,
                artifacts: "results/**/test.xml",
                fingerprint: true,
            );
            test_jenkins_helper.analyse_issues("JUNIT", "results/**/test.xml");
        }
    }

    stage("Publish test results") {
        xunit(
            checksName: "winagt-build-linux",
            tools: [
                Custom(
                    customXSL: "${checkout_dir}/buildscripts/scripts/schema/pytest-xunit.xsl",
                    deleteOutputFiles: false,
                    failIfNotNew: false,
                    pattern: "checkout/results/**/test.xml",
                    skipNoTestFiles: false,
                    stopProcessingIfError: true,
                )
            ]
        );
    }
}

void sign_windows_binaries(String branch_name, String cmk_version, String binary_directory) {
    def windows = load("${checkout_dir}/buildscripts/scripts/utils/windows.groovy");

    withCredentials([
        string(credentialsId: "azure_artifact_signing_client_secret", variable: "AZURE_ARTIFACT_SIGNING_CLIENT_SECRET"),
        string(credentialsId: "azure_artifact_signing_correlation_suffix", variable: "AZURE_ARTIFACT_SIGNING_CORRELATION_SUFFIX"),
    ]) {
        // Assembled inside the binding block: the suffix is only available there.
        def correlation_id = windows.azure_signing_correlation_id(branch_name);
        withEnv([
            "AZURE_ARTIFACT_SIGNING_ENDPOINT=${env.AZURE_ARTIFACT_SIGNING_ENDPOINT}",
            "AZURE_ARTIFACT_SIGNING_ACCOUNT=${env.AZURE_ARTIFACT_SIGNING_ACCOUNT}",
            "AZURE_ARTIFACT_SIGNING_PROFILE=${env.AZURE_ARTIFACT_SIGNING_PROFILE}",
            "AZURE_ARTIFACT_SIGNING_TENANT_ID=${env.AZURE_ARTIFACT_SIGNING_TENANT_ID}",
            "AZURE_ARTIFACT_SIGNING_CLIENT_ID=${env.AZURE_ARTIFACT_SIGNING_CLIENT_ID}",
            "AZURE_ARTIFACT_SIGNING_CORRELATION_ID=${correlation_id}",
        ]) {
            // The package build and the bakery also need each MSI unsigned
            // (check_mk_agent_unsigned.msi, see cmk/utils/msi_engine.py), so
            // keep a copy and sign everything else.
            sh(
                """
                set -euo pipefail
                for msi in ${binary_directory}/*.msi; do
                    cp -f "\$msi" "\${msi%.msi}_unsigned.msi"
                done
                bazel run --cmk_version=${cmk_version} //agents/wnx/scripts:sign_azure -- \\
                    \$(find ${binary_directory} -maxdepth 1 -type f ! -name '*_unsigned.msi' | sort)
                """
            );
        }
    }
}

/// Merges the bazel test.xml files into results/ and makes them digestible for
/// the publish step.
void collect_test_results() {
    sh(
        """
        set -euo pipefail
        BAZEL_TEST_LOGS_DEST=results buildscripts/scripts/bazel_test_post_archive_xunit.sh || :
        bazel --run_under="cd \$PWD &&" run //buildscripts/scripts:collect_rust_tests -- results results || :
        # watest reports through googletest's XML writer, whose
        # <testsuites disabled= timestamp=> attributes the pytest XSL
        # of the publish step below rejects.
        sed -i '/<testsuites /{s/ disabled="[0-9]*"//;s/ timestamp="[^"]*"//;}' \\
            results/agents/wnx/watest-wine/test.xml || :
        """
    );
}

return this;
