#!groovy

/// file: trigger-cmk-distro-package.groovy

/// Triggers builds of all artifacts required to build a distribution package
/// (.rpm, .dep, etc.) for a given edition/distribution at a given git hash
/// triggers the actual package build after all required artifacts are available
/// and finally triggers the signing job. If any of these steps fail no onwards
/// jobs are started to save resources

// groovylint-disable MethodSize
void main() {
    check_job_parameters([
        ["EDITION", true],
        ["DISTRO", true],
        ["VERSION", true],
        "CIPARAM_OVERRIDE_DOCKER_TAG_BUILD",
        "DISABLE_CACHE",
        // TODO: Rename to FAKE_AGENT_ARTIFACTS -> we're also faking the linux updaters now
        "FAKE_WINDOWS_ARTIFACTS",
    ]);

    def distro = params.DISTRO;
    def edition = params.EDITION;
    def version = params.VERSION;
    def disable_cache = params.DISABLE_CACHE;

    def versioning = load("${checkout_dir}/buildscripts/scripts/utils/versioning.groovy");
    def package_helper = load("${checkout_dir}/buildscripts/scripts/utils/package_helper.groovy");

    def safe_branch_name = versioning.safe_branch_name();
    def branch_version = versioning.get_branch_version(checkout_dir);
    def branch_base_folder = package_helper.branch_base_folder(false);

    def cmk_version_rc_aware = versioning.get_cmk_version(safe_branch_name, branch_version, version);
    def cmk_version = versioning.strip_rc_number_from_version(cmk_version_rc_aware);

    def causes = currentBuild.getBuildCauses();
    def triggerd_by = "";
    for (cause in causes) {
        if (cause.upstreamProject != null) {
            triggerd_by += cause.upstreamProject + "/" + cause.upstreamBuild + "\n";
        }
    }
    def bazel_log_prefix = "bazel_log_";

    print(
        """
        |===== CONFIGURATION ===============================
        |distro:................... │${distro}│
        |edition:.................. │${edition}│
        |safe_branch_name:......... │${safe_branch_name}│
        |checkout_dir:............. │${checkout_dir}│
        |triggerd_by:.............. │${triggerd_by}│
        |===================================================
        """.stripMargin());

    // this is a quick fix for FIPS based tests, see CMK-20851
    if (params.CIPARAM_OVERRIDE_BUILD_NODE == "fips") {
        // Builds can not be done on FIPS node
        error("Package builds can not be done on FIPS node");
    }

    // to get the same path hash as the sub jobs triggered by this job, the "Prepare workspace" has to be done here
    // as the sub jobs do this task as well and here a different Windows build would be requested compared to the sub jobs
    stage("Prepare workspace") {
        inside_container_minimal(safe_branch_name: safe_branch_name) {
            dir("${checkout_dir}") {
                versioning.configure_checkout_folder(edition, cmk_version);
            }
        }
    }

    inside_container_minimal(safe_branch_name: safe_branch_name) {
        def stages = [
            "Trigger Build BOM": {
                smart_stage(
                    name: "Trigger Build BOM",
                    raiseOnError: true,
                ) {
                    smart_build(
                        // see global-defaults.yml, needs to run in minimal container
                        use_upstream_build: true,
                        relative_job_name: "${branch_base_folder}/builders/build-cmk-bom",
                        build_params: [
                            CUSTOM_GIT_REF: effective_git_ref,
                            VERSION: version,
                            EDITION: edition,
                            DISABLE_CACHE: disable_cache,
                        ],
                        build_params_no_check: [
                            CIPARAM_OVERRIDE_BUILD_NODE: params.CIPARAM_OVERRIDE_BUILD_NODE,
                            CIPARAM_CLEANUP_WORKSPACE: params.CIPARAM_CLEANUP_WORKSPACE,
                            CIPARAM_BISECT_COMMENT: params.CIPARAM_BISECT_COMMENT,
                        ],
                        download: false,
                    );
                }
            },
        ];

        if (!params.FAKE_WINDOWS_ARTIFACTS) {
            stages += package_helper.provide_agent_binaries(
                version: version,
                cmk_version: cmk_version,
                edition: edition,
                disable_cache: disable_cache,
                bisect_comment: params.CIPARAM_BISECT_COMMENT,
                move_artifacts: false,
            );
        }

        // execute Windows agent, windows modules, linux agent and BOM in parallel
        currentBuild.result = parallel(stages).values().every { it } ? "SUCCESS" : "FAILURE";

        smart_stage(
            name: "Trigger Build package",
            condition: currentBuild.result == "SUCCESS",
            raiseOnError: true,
        ) {
            smart_build(
                // see global-defaults.yml, needs to run in minimal container
                use_upstream_build: true,
                relative_job_name: "${branch_base_folder}/builders/build-cmk-distro-package",
                build_params: [
                    CUSTOM_GIT_REF: effective_git_ref,
                    VERSION: version,
                    EDITION: edition,
                    DISTRO: distro,
                    DISABLE_CACHE: disable_cache,
                    FAKE_WINDOWS_ARTIFACTS: params.FAKE_WINDOWS_ARTIFACTS,
                    CIPARAM_OVERRIDE_DOCKER_TAG_BUILD: params.CIPARAM_OVERRIDE_DOCKER_TAG_BUILD,
                ],
                build_params_no_check: [
                    CIPARAM_OVERRIDE_BUILD_NODE: params.CIPARAM_OVERRIDE_BUILD_NODE,
                    CIPARAM_CLEANUP_WORKSPACE: params.CIPARAM_CLEANUP_WORKSPACE,
                    CIPARAM_BISECT_COMMENT: params.CIPARAM_BISECT_COMMENT,
                ],
                no_remove_others: true, // do not delete other files in the dest dir
                download: true,
                dest: "${checkout_dir}",
            );
        }

        smart_stage(
            name: "Trigger Sign package",
            condition: currentBuild.result == "SUCCESS",
            raiseOnError: true,
        ) {
            smart_build(
                // see global-defaults.yml, needs to run in minimal container
                use_upstream_build: true,
                relative_job_name: "${branch_base_folder}/builders/sign-cmk-distro-package",
                build_params: [
                    CUSTOM_GIT_REF: effective_git_ref,
                    VERSION: version,
                    EDITION: edition,
                    DISTRO: distro,
                    DISABLE_CACHE: disable_cache,
                    FAKE_WINDOWS_ARTIFACTS: params.FAKE_WINDOWS_ARTIFACTS,
                ],
                build_params_no_check: [
                    CIPARAM_OVERRIDE_BUILD_NODE: params.CIPARAM_OVERRIDE_BUILD_NODE,
                    CIPARAM_CLEANUP_WORKSPACE: params.CIPARAM_CLEANUP_WORKSPACE,
                    CIPARAM_BISECT_COMMENT: params.CIPARAM_BISECT_COMMENT,
                ],
                no_remove_others: true, // do not delete other files in the dest dir
                download: true,
                dest: "${checkout_dir}",
            );
        }
    }

    stage("Archive stuff") {
        dir("${checkout_dir}") {
            show_duration("archiveArtifacts") {
                archiveArtifacts(
                    artifacts: "*.deb, *.rpm, *.cma, ${bazel_log_prefix}*, omd/bill-of-materials.json",
                    fingerprint: true,
                );
            }
        }
    }
}

return this;
