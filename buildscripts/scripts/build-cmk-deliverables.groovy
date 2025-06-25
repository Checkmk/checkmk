#!groovy

/// file: build-cmk-deliverables.groovy

/// Some decisions have been made in order to move forward but should be discussed:
///  - trigger agent updater builds here or in each job individually?
///  - tailor also triggers tests?
///  - abort on failures?

import org.jenkinsci.plugins.pipeline.modeldefinition.Utils


/// Builds all artifacts used for a given Checkmk edition
def main() {
    check_job_parameters([
        ["EDITION", true],
        ["VERSION", true],  // should be deprecated
        ["OVERRIDE_DISTROS", false],
        ["USE_CASE", true],
        ["CIPARAM_OVERRIDE_DOCKER_TAG_BUILD", false],
        ["CIPARAM_REMOVE_RC_CANDIDATES", false],
        ["SKIP_DEPLOY_TO_WEBSITE", false],
        ["DISABLE_CACHE", false],
        ["FAKE_WINDOWS_ARTIFACTS", false],
    ]);

    check_environment_variables([
        "INTERNAL_DEPLOY_URL",
        "INTERNAL_DEPLOY_DEST",
        "INTERNAL_DEPLOY_PORT",
        "ARTIFACT_STORAGE",
        "DOCKER_REGISTRY",
    ]);

    def versioning = load("${checkout_dir}/buildscripts/scripts/utils/versioning.groovy");
    def artifacts_helper = load("${checkout_dir}/buildscripts/scripts/utils/upload_artifacts.groovy");
    def package_helper = load("${checkout_dir}/buildscripts/scripts/utils/package_helper.groovy");
    def bazel_logs = load("${checkout_dir}/buildscripts/scripts/utils/bazel_logs.groovy");

    /// Might also be taken from editions.yml - there we also have "saas" and "raw" but
    /// AFAIK there is no way to extract the editions we want to test generically, so we
    /// hard-code these:
    def all_distros = versioning.get_distros(override: "all");
    def selected_distros = versioning.get_distros(
        edition: params.EDITION,
        use_case: params.USE_CASE,
        override: params.OVERRIDE_DISTROS);
    def safe_branch_name = versioning.safe_branch_name();
    def branch_version = versioning.get_branch_version(checkout_dir);

    /// This will get us the location to e.g. "checkmk/master" or "Testing/<name>/checkmk/master"
    def branch_base_folder = package_helper.branch_base_folder(with_testing_prefix: true);

    def cmk_version_rc_aware = versioning.get_cmk_version(safe_branch_name, branch_version, params.VERSION);
    def cmk_version = versioning.strip_rc_number_from_version(cmk_version_rc_aware);
    def relative_deliverables_dir = "deliverables/${cmk_version_rc_aware}";
    def deliverables_dir = "${WORKSPACE}/deliverables/${cmk_version_rc_aware}";
    def bazel_log_prefix = "bazel_log_";

    def upload_to_testbuilds = ! (branch_base_folder.startsWith("Testing"));
    def deploy_to_website = (
        upload_to_testbuilds
        && (! currentBuild.fullProjectName.contains("/cv/"))
        && (! params.SKIP_DEPLOY_TO_WEBSITE)
    );

    print(
        """
        |===== CONFIGURATION ===============================
        |all_distros:....................... │${all_distros}│
        |selected_distros:.................. │${selected_distros}│
        |EDITION:........................... │${params.EDITION}│
        |VERSION:........................... │${params.VERSION}│
        |USE_CASE:.......................... │${params.USE_CASE}│
        |CIPARAM_REMOVE_RC_CANDIDATES:...... │${params.CIPARAM_REMOVE_RC_CANDIDATES}│
        |CIPARAM_OVERRIDE_DOCKER_TAG_BUILD:. │${params.CIPARAM_OVERRIDE_DOCKER_TAG_BUILD}│
        |FAKE_WINDOWS_ARTIFACTS:............ │${params.FAKE_WINDOWS_ARTIFACTS}│
        |cmk_version:....................... │${cmk_version}│
        |cmk_version_rc_aware:.............. │${cmk_version_rc_aware}│
        |relative_deliverables_dir:......... │${relative_deliverables_dir}│
        |upload_to_testbuilds:.............. │${upload_to_testbuilds}│
        |deploy_to_website:................. │${deploy_to_website}│
        |branch_base_folder:................ │${branch_base_folder}│
        |===================================================
        """.stripMargin());

    /// In order to ensure a fixed order for stages executed in parallel,
    /// we wait an increasing amount of time (N * 100ms).
    /// Without this we end up with a capped build overview matrix in the job view (Jenkins doesn't
    /// like changing order or amount of stages, which will happen with stages started `via parallel()`
    def timeOffsetForOrder = 0;

    def stages = [
        "Build source package": {
            sleep(0.1 * timeOffsetForOrder++);
            def build_instance = null;

            smart_stage(
                name: "Build source package",
                raiseOnError: false,
            ) {
                build_instance = smart_build(
                    // see global-defaults.yml, needs to run in minimal container
                    use_upstream_build: true,
                    relative_job_name: "${branch_base_folder}/builders/build-cmk-source_tgz",
                    build_params: [
                        CUSTOM_GIT_REF: effective_git_ref,
                        VERSION: params.VERSION,
                        EDITION: params.EDITION,
                        DISABLE_CACHE: params.DISABLE_CACHE,
                        FAKE_WINDOWS_ARTIFACTS: params.FAKE_WINDOWS_ARTIFACTS,
                    ],

                    build_params_no_check: [
                        CIPARAM_OVERRIDE_BUILD_NODE: params.CIPARAM_OVERRIDE_BUILD_NODE,
                        CIPARAM_CLEANUP_WORKSPACE: params.CIPARAM_CLEANUP_WORKSPACE,
                        CIPARAM_BISECT_COMMENT: params.CIPARAM_BISECT_COMMENT,
                    ],
                    no_remove_others: true, // do not delete other files in the dest dir
                    download: false,    // use copyArtifacts to avoid nested directories
                );
            }
            smart_stage(
                name: "Copy artifacts",
                condition: build_instance,
                raiseOnError: false,
            ) {
                copyArtifacts(
                    projectName: "${branch_base_folder}/builders/build-cmk-source_tgz",
                    selector: specific(build_instance.getId()),
                    target: relative_deliverables_dir,
                    fingerprintArtifacts: true,
                )
            }
        },
        "Build BOM": {
            sleep(0.1 * timeOffsetForOrder++);
            def build_instance = null;

            smart_stage(
                name: "Build BOM",
                raiseOnError: false,
            ) {
                build_instance = smart_build(
                    // see global-defaults.yml, needs to run in minimal container
                    use_upstream_build: true,
                    relative_job_name: "${branch_base_folder}/builders/build-cmk-bom",
                    build_params: [
                        CUSTOM_GIT_REF: effective_git_ref,
                        VERSION: params.VERSION,
                        EDITION: params.EDITION,
                        DISABLE_CACHE: params.DISABLE_CACHE,
                    ],
                    build_params_no_check: [
                        CIPARAM_OVERRIDE_BUILD_NODE: params.CIPARAM_OVERRIDE_BUILD_NODE,
                        CIPARAM_CLEANUP_WORKSPACE: params.CIPARAM_CLEANUP_WORKSPACE,
                        CIPARAM_BISECT_COMMENT: params.CIPARAM_BISECT_COMMENT,
                    ],
                    no_remove_others: true, // do not delete other files in the dest dir
                    download: false,    // use copyArtifacts to avoid nested directories
                );
            }
            smart_stage(
                name: "Copy artifacts",
                condition: build_instance,
                raiseOnError: false,
            ) {
                copyArtifacts(
                    projectName: "${branch_base_folder}/builders/build-cmk-bom",
                    selector: specific(build_instance.getId()),
                    target: relative_deliverables_dir,
                    fingerprintArtifacts: true,
                )
            }
        }
    ];

    stages += all_distros.collectEntries { distro ->
        [("${distro}") : {
            sleep(0.1 * timeOffsetForOrder++);
            def run_condition = distro in selected_distros;
            def build_instance = null;

            /// this makes sure the whole parallel thread is marked as skipped
            if (! run_condition){
                Utils.markStageSkippedForConditional("${distro}");
            }

            smart_stage(
                name: "distro package ${distro}",
                condition: run_condition,
                raiseOnError: false,
            ) {
                build_instance = smart_build(
                    // see global-defaults.yml, needs to run in minimal container
                    use_upstream_build: true,
                    relative_job_name: "${branch_base_folder}/builders/build-cmk-distro-package",
                    build_params: [
                        CUSTOM_GIT_REF: effective_git_ref,
                        VERSION: params.VERSION,
                        EDITION: params.EDITION,
                        DISTRO: distro,
                        DISABLE_CACHE: params.DISABLE_CACHE,
                        CIPARAM_OVERRIDE_DOCKER_TAG_BUILD: params.CIPARAM_OVERRIDE_DOCKER_TAG_BUILD,
                        FAKE_WINDOWS_ARTIFACTS: params.FAKE_WINDOWS_ARTIFACTS,
                    ],
                    build_params_no_check: [
                        CIPARAM_OVERRIDE_BUILD_NODE: params.CIPARAM_OVERRIDE_BUILD_NODE,
                        CIPARAM_CLEANUP_WORKSPACE: params.CIPARAM_CLEANUP_WORKSPACE,
                        CIPARAM_BISECT_COMMENT: params.CIPARAM_BISECT_COMMENT,
                    ],
                    no_remove_others: true, // do not delete other files in the dest dir
                    download: false,    // use copyArtifacts to avoid nested directories
                );
            }
            smart_stage(
                name: "Copy artifacts",
                condition: run_condition && build_instance,
                raiseOnError: false,
            ) {
                copyArtifacts(
                    projectName: "${branch_base_folder}/builders/build-cmk-distro-package",
                    selector: specific(build_instance.getId()),
                    target: relative_deliverables_dir,
                    fingerprintArtifacts: true,
                )
            }
        }]
    }

    inside_container_minimal(safe_branch_name: safe_branch_name) {
        currentBuild.result = parallel(stages).values().every { it } ? "SUCCESS" : "FAILURE";
    }

    smart_stage(
        name: "Upload artifacts",
        condition: upload_to_testbuilds,
    ) {
        dir("${deliverables_dir}") {
            /// BOM shall have a unique name, see CMK-16483
            // TODO: We should really let bazel generate the correct file name - we're already passing edition and version to bazel build
            sh("""
                cp omd/bill-of-materials.json check-mk-${params.EDITION}-${cmk_version}-bill-of-materials.json
                cp omd/bill-of-materials.csv check-mk-${params.EDITION}-${cmk_version}-bill-of-materials.csv
            """);
        }

        /// File.eachFileRecurse works on Jenkins master node only, so we have to build it
        /// on our own..
        def files_to_upload = {
            dir("${deliverables_dir}") {
                cmd_output("ls *.{deb,rpm,cma,tar.gz,json,csv} || true").split().toList();
            }
        }();
        print("Found files to upload: ${files_to_upload}");

        def filtered_files_to_upload = [];
        files_to_upload.each { item ->
            if (!item.startsWith(bazel_log_prefix)) {
                filtered_files_to_upload += item;
            }
        }
        print("Filtered files to upload: ${filtered_files_to_upload}")

        filtered_files_to_upload.each { filename ->
            artifacts_helper.upload_via_rsync(
                "${WORKSPACE}/deliverables",
                "${cmk_version_rc_aware}",
                "${filename}",
                "${INTERNAL_DEPLOY_DEST}",
                INTERNAL_DEPLOY_PORT,
            );
        }

        currentBuild.description += """\
            <p><a href='${INTERNAL_DEPLOY_URL}/${cmk_version}'>Download Artifacts</a></p>
            """.stripIndent();

        // this must not be called from within the container (results in yaml package missing)
        def exclude_pattern = versioning.get_internal_artifacts_pattern();
        artifacts_helper.upload_version_dir(
            deliverables_dir,
            WEB_DEPLOY_DEST,
            WEB_DEPLOY_PORT,
            EXCLUDE_PATTERN=exclude_pattern,
        );

        if (EDITION.toLowerCase() == "saas" && versioning.is_official_release(cmk_version_rc_aware)) {
            // uploads distro packages, source.tar.gz and hashes
            artifacts_helper.upload_files_to_nexus(
                "${deliverables_dir}/check-mk-saas-${cmk_version}*",
                "${ARTIFACT_STORAGE}/repository/saas-patch-releases/",
            );
        }
    }

    smart_stage(
        name: "Deploy to website",
        condition: deploy_to_website,
    ) {
        smart_build(
            job: "${branch_base_folder}/deploy-to-website",
            parameters: [
                stringParam(name: "VERSION", value: params.VERSION),
                booleanParam(name: "CIPARAM_REMOVE_RC_CANDIDATES", value: params.CIPARAM_REMOVE_RC_CANDIDATES),

                // default parameters
                stringParam(name: "CUSTOM_GIT_REF", value: effective_git_ref),
                booleanParam(name: "DISABLE_CACHE", value: params.DISABLE_CACHE),
                stringParam(name: "CIPARAM_OVERRIDE_BUILD_NODE", value: params.CIPARAM_OVERRIDE_BUILD_NODE),
                stringParam(name: "CIPARAM_CLEANUP_WORKSPACE", value: params.CIPARAM_CLEANUP_WORKSPACE),
                stringParam(name: "CIPARAM_BISECT_COMMENT", value: params.CIPARAM_BISECT_COMMENT),
            ]
        );
    }

    smart_stage(name: "Plot cache hits") {
        dir("${deliverables_dir}") {
            bazel_logs.try_plot_cache_hits("${bazel_log_prefix}", selected_distros);
        }
    }

    smart_stage(name: "Cleanup leftovers") {
        dir("${deliverables_dir}") {
            sh("rm -rf *.deb *.rpm *.cma *.tar.gz *.hash");
        }
    }

    smart_stage(name: "Archive artifacts") {
        dir("${deliverables_dir}") {
            show_duration("archiveArtifacts") {
                archiveArtifacts(
                    artifacts: "${bazel_log_prefix}*",
                    fingerprint: true,
                );
            }
        }
    }
}

return this;
