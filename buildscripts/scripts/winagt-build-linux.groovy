#!groovy

/// file: winagt-build-linux.groovy
///
/// Builds the Windows agent artifacts that can be produced on Linux --
/// currently the Rust binaries (cmk-agent-ctl, mk-sql, mk-oracle), cross
/// compiled via the xwin toolchain (//bazel/toolchains/cc/xwin, CMK-34215)
/// -- and runs their unit tests under the pinned Wine and asserts that
/// their PE import tables are free of dynamic-CRT references. Test
/// results are published with one JUnit testcase per Rust test (via
/// collect_rust_tests).
///
/// The job grows with each artifact the cross-compile work makes
/// producible (unsigned MSI and service exe with CMK-34218/CMK-34220,
/// signed artifacts with CMK-34221) until it reaches winagt-build parity
/// and can replace the Windows-node job.

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
    def targets = [
        "//packages/cmk-agent-ctl:cmk-agent-ctl-windows",
        "//packages/mk-sql:mk-sql-windows",
        "//packages/mk-oracle:mk-oracle-windows",
    ];
    // The Wine unit-test tiers of the targets above (a separate list:
    // not every artifact has one).
    def wine_test_targets = [
        "//packages/cmk-agent-ctl:cmk-agent-ctl-tests-wine",
        "//packages/mk-sql:mk-sql-tests-wine",
        "//packages/mk-oracle:mk-oracle-tests-wine",
    ];
    def target_args = targets.join(" ");
    def crt_test_args = targets.collect { it + "-static-crt" }.join(" ");
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
                // Merge the bazel test.xml files into results/, then expand
                // the libtest output the wine tiers stream through their
                // sh_test into one JUnit testcase per Rust test (the
                // static-CRT checks stay one testcase per target).
                sh(
                    """
                    set -euo pipefail
                    BAZEL_TEST_LOGS_DEST=results buildscripts/scripts/bazel_test_post_archive_xunit.sh || :
                    bazel --run_under="cd \$PWD &&" run //buildscripts/scripts:collect_rust_tests -- results results || :
                    """
                );
            }
        }

        stage("Archive binaries") {
            dir("artefacts") {
                archiveArtifacts(
                    artifacts: "*.exe",
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

return this;
