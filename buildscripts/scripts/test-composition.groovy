#!groovy

/// file: test-composition.groovy

import org.jenkinsci.plugins.pipeline.modeldefinition.Utils

// groovylint-disable MethodSize
void main() {
    check_job_parameters([
        "CIPARAM_OVERRIDE_DOCKER_TAG_BUILD",
        "EDITION",
        "FAKE_ARTIFACTS",
        "OVERRIDE_DISTROS",
        "USE_CASE",
        "VERSION",
    ]);

    def versioning = load("${checkout_dir}/buildscripts/scripts/utils/versioning.groovy");
    def package_helper = load("${checkout_dir}/buildscripts/scripts/utils/package_helper.groovy");

    /// This will get us the location to e.g. "checkmk/master" or "Testing/<name>/checkmk/master"
    def branch_base_folder = package_helper.branch_base_folder(true);
    def safe_branch_name = versioning.safe_branch_name();
    def branch_version = versioning.get_branch_version(checkout_dir);
    def cmk_version_rc_aware = versioning.get_cmk_version(safe_branch_name, branch_version, params.VERSION);
    def cmk_version = versioning.strip_rc_number_from_version(cmk_version_rc_aware);
    def docker_tag = versioning.select_docker_tag(
        params.CIPARAM_OVERRIDE_DOCKER_TAG_BUILD,  // 'build tag'
        safe_branch_name,                   // 'branch' returns '<BRANCH>-latest'
    );

    // When building from a git tag (VERSION != "daily"), we cannot get the branch name from the scm so used defines.make instead.
    // this is save on master as there are no tags/versions built other than daily
    def branch_name = (params.VERSION == "daily") ? safe_branch_name : branch_version;
    def disable_cache = params.DISABLE_CACHE;
    def disable_signing = params.DISABLE_CMK_DISTRO_PACKAGE_SIGNING;
    def fake_artifacts = params.FAKE_ARTIFACTS;
    def force_build = params.DISABLE_JENKINS_CACHE == true;
    def use_case = (params.USE_CASE == "fips") ? params.USE_CASE : "daily_tests";

    def all_distros = [];
    def deliverables_dir = "${checkout_dir}/test-results";
    def relative_job_name = "${branch_base_folder}/builders/test-composition-single";
    def selected_distros = [];

    inside_container_minimal(safe_branch_name: safe_branch_name) {
        // run everything requiring python in this container
        all_distros = versioning.get_distros(override: "all");
        selected_distros = versioning.get_distros(
            edition: params.EDITION,
            use_case: use_case,
            override: params.OVERRIDE_DISTROS
        );
    }

    currentBuild.description += (
        """
        |Run composition tests for<br>
        |EDITION: ${params.EDITION}<br>
        |selected_distros: ${selected_distros}<br>
        |VERSION: ${params.VERSION}<br>
        """.stripMargin());

    print(
        """
        |===== CONFIGURATION ===============================
        |branch_name:.............. │${branch_name}│
        |branch_version:........... │${branch_version}│
        |cmk_version:.............. │${cmk_version}│
        |cmk_version_rc_aware:..... │${cmk_version_rc_aware}│
        |deliverables_dir:......... │${deliverables_dir}│
        |disable_cache:............ │${disable_cache}│
        |disable_signing:.......... │${disable_signing}│
        |docker_tag:............... │${docker_tag}│
        |fake_artifacts:........... │${fake_artifacts}│
        |force_build:.............. │${force_build}│
        |safe_branch_name:......... │${safe_branch_name}│
        |selected_distros:......... │${selected_distros}│
        |===================================================
        """.stripMargin());

    /// avoid failures due to leftover artifacts from prior runs
    /// and create folder before entering containers to not delete the folder after leaving the container
    stage("Prepare workspace") {
        dir("${checkout_dir}") {
            sh("""
                rm -rf ${deliverables_dir}
                mkdir ${deliverables_dir}
            """);
        }
    }

    def test_stages = all_distros.collectEntries { distro -> [
        ("Test ${distro}") : {
            def stepName = "Test ${distro}";
            def run_condition = distro in selected_distros;

            /// this makes sure the whole parallel thread is marked as skipped
            if (! run_condition) {
                Utils.markStageSkippedForConditional(stepName);
            }

            smart_stage(
                name: stepName,
                condition: run_condition,
                raiseOnError: false,
            ) {
                smart_build(
                    // see global-defaults.yml, needs to run in minimal container
                    use_upstream_build: true,
                    force_build: force_build,
                    relative_job_name: relative_job_name,
                    build_params: [
                        DISTRO: distro,
                        EDITION: params.EDITION,
                        CUSTOM_GIT_REF: effective_git_ref,
                        FAKE_ARTIFACTS: fake_artifacts,
                        DISABLE_CACHE: disable_cache,
                        DISABLE_CMK_DISTRO_PACKAGE_SIGNING: disable_signing,
                        // FIPS node specifier has to be respected
                        CIPARAM_OVERRIDE_BUILD_NODE: (params.USE_CASE == "fips") ? "fips" : params.CIPARAM_OVERRIDE_BUILD_NODE,
                    ],
                    build_params_no_check: [
                        CIPARAM_CLEANUP_WORKSPACE: params.CIPARAM_CLEANUP_WORKSPACE,
                        CIPARAM_BISECT_COMMENT: params.CIPARAM_BISECT_COMMENT,
                    ],
                    no_remove_others: true, // do not delete other files in the dest dir
                    download: true,
                    dest: deliverables_dir,
                );
            }
        }]
    }

    inside_container_minimal(safe_branch_name: safe_branch_name) {
        currentBuild.result = parallel(test_stages).values().every { it } ? "SUCCESS" : "FAILURE";
    }

    stage("Archive / process test reports") {
        dir("${checkout_dir}") {
            show_duration("archiveArtifacts") {
                archiveArtifacts(
                    allowEmptyArchive: true,
                    artifacts: "test-results/**",
                    fingerprint: true,
                );
            }
        }
        xunit([Custom(
            customXSL: "${checkout_dir}/buildscripts/scripts/schema/pytest-xunit.xsl",
            deleteOutputFiles: true,
            failIfNotNew: false,    // as they are copied from the single tests
            pattern: "checkout/test-results/**/junit.xml",
            skipNoTestFiles: false,
            stopProcessingIfError: true
        )]);
    }
}

return this;
