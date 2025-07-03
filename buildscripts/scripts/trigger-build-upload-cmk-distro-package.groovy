#!groovy

/// file: trigger-build-upload-cmk-distro-package.groovy

/// Triggers a distribution package build (.rpm, .dep, etc.) for a given
/// edition/distribution at a given git hash and uploads it to the tstsbuild server

def main() {
    check_job_parameters([
        "EDITION",
        "DISTRO",
        "VERSION",
        "FAKE_WINDOWS_ARTIFACTS",
        "TRIGGER_POST_SUBMIT_HEAVY_CHAIN",
    ]);

    def single_tests = load("${checkout_dir}/buildscripts/scripts/utils/single_tests.groovy");
    def versioning = load("${checkout_dir}/buildscripts/scripts/utils/versioning.groovy");
    def artifacts_helper = load("${checkout_dir}/buildscripts/scripts/utils/upload_artifacts.groovy");
    def package_helper = load("${checkout_dir}/buildscripts/scripts/utils/package_helper.groovy");
    def notify = load("${checkout_dir}/buildscripts/scripts/utils/notify.groovy");

    def distro = params.DISTRO;
    def fake_windows_artifacts = params.FAKE_WINDOWS_ARTIFACTS;
    def trigger_post_submit_heavy_chain = params.TRIGGER_POST_SUBMIT_HEAVY_CHAIN;
    def build_node = params.CIPARAM_OVERRIDE_BUILD_NODE;

    def safe_branch_name = versioning.safe_branch_name();
    def branch_version = versioning.get_branch_version(checkout_dir);
    def branch_name = safe_branch_name;
    def cmk_version_rc_aware = versioning.get_cmk_version(safe_branch_name, branch_version, VERSION);
    def cmk_version = versioning.strip_rc_number_from_version(cmk_version_rc_aware);

    /// This will get us the location to e.g. "checkmk/master" or "Testing/<name>/checkmk/master"
    def branch_base_folder = package_helper.branch_base_folder(with_testing_prefix: true);

    // Use the directory also used by tests/testlib/containers.py to have it find
    // the downloaded package.
    def download_dir = "package_download";
    def setup_values = single_tests.common_prepare(version: "daily");
    def all_editions = ["cloud", "enterprise", "managed", "raw", "saas", params.EDITION].unique();

    print(
        """
        |===== CONFIGURATION ===============================
        |safe_branch_name:......... │${safe_branch_name}│
        |branch_name:.............. │${branch_name}│
        |cmk_version:.............. │${cmk_version}│
        |cmk_version_rc_aware:..... │${cmk_version_rc_aware}│
        |branch_version:........... │${branch_version}│
        |all_editions:............. │${all_editions}│
        |distro:................... │${distro}│
        |checkout_dir:............. │${checkout_dir}│
        |branch_base_folder:....... │${branch_base_folder}│
        |===================================================
        """.stripMargin());


    if (build_node == "fips") {
        // Do not start builds on FIPS node
        println("Detected build node 'fips', switching this to 'fra'.");
        build_node = "fra"
    }

    def stages = all_editions.collectEntries { edition ->
        [("${edition}") : {
            def build_instance = null;

            smart_stage(
                name: "Trigger ${edition} package build",
                raiseOnError: true,
            ) {
                build_instance = smart_build(
                    // see global-defaults.yml, needs to run in minimal container
                    use_upstream_build: true,
                    relative_job_name: "${branch_base_folder}/builders/build-cmk-distro-package",
                    build_params: [
                        CUSTOM_GIT_REF: effective_git_ref,
                        VERSION: params.VERSION,
                        EDITION: edition,
                        DISTRO: distro,
                        DISABLE_CACHE: params.DISABLE_CACHE,
                        CIPARAM_OVERRIDE_DOCKER_TAG_BUILD: setup_values.docker_tag,
                        FAKE_WINDOWS_ARTIFACTS: fake_windows_artifacts,
                    ],
                    build_params_no_check: [
                        CIPARAM_OVERRIDE_BUILD_NODE: build_node,
                        CIPARAM_CLEANUP_WORKSPACE: params.CIPARAM_CLEANUP_WORKSPACE,
                        CIPARAM_BISECT_COMMENT: params.CIPARAM_BISECT_COMMENT,
                    ],
                    no_remove_others: true, // do not delete other files in the dest dir
                    download: false,    // use copyArtifacts to avoid nested directories
                );
            }

            if ("${build_instance.result}" != "SUCCESS") {
                notify.notify_maintainer_of_package("${TEAM_CI_MAIL}".split(","), edition, "${build_instance.absoluteUrl}")
            }

            // Without this stage in place the whole job would fail, unclear why
            smart_stage(
                name: "Say hello",
                condition: build_instance,
                raiseOnError: true,
            ) {
                sh("echo hello");
            }
        }]
    }

    inside_container_minimal(safe_branch_name: safe_branch_name) {
        currentBuild.result = parallel(stages).values().every { it } ? "SUCCESS" : "FAILURE";
    }

    smart_stage(
        name: "Trigger trigger-post-submit-test-cascade-heavy",
        condition: trigger_post_submit_heavy_chain,
    ) {
        build(
            job: "${branch_base_folder}/trigger-post-submit-test-cascade-heavy",
            parameters: [
                stringParam(name: "CUSTOM_GIT_REF", value: effective_git_ref),
                stringParam(name: "CIPARAM_OVERRIDE_BUILD_NODE", value: CIPARAM_OVERRIDE_BUILD_NODE),
                stringParam(name: "CIPARAM_CLEANUP_WORKSPACE", value: CIPARAM_CLEANUP_WORKSPACE),
                stringParam(name: "CIPARAM_BISECT_COMMENT", value: CIPARAM_BISECT_COMMENT),
            ],
            wait: false,
        );
    }
}

return this;
