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
    // The exes the MSI embeds, signed during the build (msi_* in
    // agents/wnx/BUILD.bazel). Archived as embedded and not signed again
    // afterwards: one signature, and the archived file is the one in the
    // MSI, like run.ps1 ships it.
    def msi_exe_targets = [
        "//packages/cmk-agent-ctl:cmk-agent-ctl-windows": "//agents/wnx:msi_cmk-agent-ctl",
    ];
    // Signed in the build, copied to the given path below the artifacts
    // directory. The plugin tar gets the name winagt-build gives it. The
    // agent exe is only hashed into windows_files_hashes.txt: nothing
    // consumes it on its own (see winagt-build-linux in
    // package_helper.groovy), and the archive pattern does not reach into
    // subdirectories.
    def renamed_targets = [
        "//agents/wnx:msi_check_mk_service": "unarchived/check_mk_service.exe",
        "//agents/windows/plugins:azure_signed_plugins": "signed_plugins.tar",
    ];
    def signed_in_build = ["cmk-agent-ctl.exe", "signed_plugins.tar"];
    // Built and archived like the binaries, but there is no -static-crt tier
    // for an MSI to check.
    def targets = exe_targets.collect { msi_exe_targets[it] ?: it } + [
        "//agents/wnx:check_mk_agent_msi",
    ];
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
    def test_stages = [
        "Check toolchain argument contract": toolchain_test_targets,
        "Run unit tests under Wine": wine_test_targets,
        "Check static CRT": exe_targets.collect { it + "-static-crt" },
    ];

    dir("${checkout_dir}") {
        def container_name = "testing-ubuntu-2204-checkmk-${safe_branch_name.replace('.', '-')}";
        container(container_name) {
            if (disable_cache) {
                sh("rm -rf remote.bazelrc");
            }

            stage("Build windows binaries") {
                build_windows_binaries(
                    safe_branch_name, cmk_version, targets, renamed_targets, "artefacts"
                );
            }

            run_test_stages(cmk_version, test_stages);

            stage("Collect test results") {
                collect_test_results();
            }

            // After the tests (they use the bazel outputs, not artefacts/).
            // No catchError on purpose: if signing fails, the job fails
            // right away and archives nothing, so unsigned or partially
            // signed binaries are never published.
            stage("Sign windows binaries") {
                sign_windows_binaries(safe_branch_name, cmk_version, "artefacts", signed_in_build);
            }

            // After signing: the hashes are taken of the signed binaries.
            stage("Add hashes") {
                add_hashes("artefacts");
            }
        }

        stage("Archive binaries") {
            dir("artefacts") {
                archiveArtifacts(
                    artifacts: "*.exe,*.msi,*.tar,*.txt",
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

void build_windows_binaries(
    String branch_name, String cmk_version, List targets, Map renamed_targets, String binary_directory
) {
    def windows = load("${checkout_dir}/buildscripts/scripts/utils/windows.groovy");

    // The MSI embeds the PowerShell scripts and exes signed during the build,
    // like the MSI winagt-build builds with --sign-azure. CMK-39886
    windows.with_azure_signing_flag(
        branch_name, "${WORKSPACE}/.azure_signing_credentials"
    ) { signing_flag ->
        sh(
            """
            set -euo pipefail
            bazel build --cmk_version=${cmk_version} ${signing_flag} \\
                ${(targets + renamed_targets.keySet()).join(" ")}
            mkdir -p ${binary_directory}/unarchived
            """
        );
        // The outputs already carry the Windows-node job's artifact
        // names (binary_name on the targets).
        targets.each { target ->
            sh(
                "cp -f \$(bazel cquery --cmk_version=${cmk_version} ${signing_flag} " +
                "--output=files ${target}) ${binary_directory}/"
            );
        }
        renamed_targets.each { target, name ->
            sh(
                "cp -f \$(bazel cquery --cmk_version=${cmk_version} ${signing_flag} " +
                "--output=files ${target}) ${binary_directory}/${name}"
            );
        }
    }
}

/// Runs each group of test targets in its own stage.
void run_test_stages(String cmk_version, Map test_stages) {
    // Fail the build but keep going, so the test results still get
    // collected and published.
    def fail_and_continue = [buildResult: 'FAILURE', stageResult: 'FAILURE'];

    test_stages.each { stage_name, test_targets ->
        stage(stage_name) {
            catchError(fail_and_continue) {
                sh(
                    """
                    set -euo pipefail
                    bazel test --cmk_version=${cmk_version} ${test_targets.join(" ")}
                    """
                );
            }
        }
    }
}

/// Adds windows_files_hashes.txt, which the package ships, see
/// Start-BinarySigning and Start-MsiSigning in agents/wnx/run.ps1.
void add_hashes(String binary_directory) {
    sh(
        """
        set -euo pipefail
        # Same format as run.ps1's Add-HashLine, in the same order: the
        # binaries, then the MSI. run.ps1 also hashes the OpenHardwareMonitor
        # files it signs; they are neither in the MSI nor in the packages, nor
        # built here, so they are left out.
        cd ${binary_directory}
        rm -f windows_files_hashes.txt
        for file in unarchived/check_mk_service.exe cmk-agent-ctl.exe mk-sql.exe mk-oracle.exe \\
            check_mk_agent.msi; do
            hash=\$(sha256sum "\$file" | cut -d' ' -f1 | tr a-f A-F)
            echo "\$(basename "\$file") \$hash" >>windows_files_hashes.txt
        done
        """
    );
}

void sign_windows_binaries(
    String branch_name, String cmk_version, String binary_directory, List signed_in_build
) {
    def windows = load("${checkout_dir}/buildscripts/scripts/utils/windows.groovy");

    // The package build and the bakery also need each MSI unsigned
    // (check_mk_agent_unsigned.msi, see cmk/utils/msi_engine.py), so
    // keep a copy and sign everything else not signed in the build.
    def files = sh(
        script: """
            set -euo pipefail
            for msi in ${binary_directory}/*.msi; do
                cp -f "\$msi" "\${msi%.msi}_unsigned.msi"
            done
            find ${binary_directory} -maxdepth 1 -type f ! -name '*_unsigned.msi' | sort
            """,
        returnStdout: true,
    ).trim().split("\n").findAll { !(it.tokenize("/").last() in signed_in_build) };
    windows.sign_with_azure(branch_name, "--cmk_version=${cmk_version}", files);
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
