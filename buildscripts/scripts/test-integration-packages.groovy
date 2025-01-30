#!groovy

/// file: test-integration-packages.groovy

/// Run integration tests for the checkmk OS packages

import org.jenkinsci.plugins.pipeline.modeldefinition.Utils

def main() {
    check_job_parameters([
        "EDITION",
        "VERSION",
        "OVERRIDE_DISTROS",
        "CIPARAM_OVERRIDE_DOCKER_TAG_BUILD",
        "USE_CASE",
    ]);

    check_environment_variables([
        "BRANCH",
    ]);

    def versioning = load("${checkout_dir}/buildscripts/scripts/utils/versioning.groovy");
    def test_jenkins_helper = load("${checkout_dir}/buildscripts/scripts/utils/test_helper.groovy");
    def package_helper = load("${checkout_dir}/buildscripts/scripts/utils/package_helper.groovy");

    /// This will get us the location to e.g. "checkmk/master" or "Testing/<name>/checkmk/master"
    def branch_base_folder = package_helper.branch_base_folder(with_testing_prefix: true);

    // TODO: we should always use USE_CASE directly from the job parameters
    def use_case = (USE_CASE == "fips") ? USE_CASE : "daily_tests"
    test_jenkins_helper.assert_fips_testing(use_case, NODE_LABELS);
    def all_distros = versioning.get_distros(override: "all");
    def selected_distros = versioning.get_distros(
        edition: EDITION,
        use_case: use_case,
        override: OVERRIDE_DISTROS
    );
    def safe_branch_name = versioning.safe_branch_name(scm);
    def branch_version = versioning.get_branch_version(checkout_dir);
    // When building from a git tag (VERSION != "daily"), we cannot get the branch name from the scm so used defines.make instead.
    // this is save on master as there are no tags/versions built other than daily
    def branch_name = (VERSION == "daily") ? safe_branch_name : branch_version;
    def cmk_version_rc_aware = versioning.get_cmk_version(safe_branch_name, branch_version, VERSION);
    def cmk_version = versioning.strip_rc_number_from_version(cmk_version_rc_aware);
    def docker_tag = versioning.select_docker_tag(
        CIPARAM_OVERRIDE_DOCKER_TAG_BUILD,  // FIXME, 'build tag'
        safe_branch_name,                   // 'branch' returns '<BRANCH>-latest'
    );

    currentBuild.description += (
        """
        |Run integration tests for packages<br>
        |VERSION: ${VERSION}<br>
        |EDITION: ${EDITION}<br>
        |selected_distros: ${selected_distros}<br>
        """.stripMargin());

    print(
        """
        |===== CONFIGURATION ===============================
        |all_distros:.............  │${all_distros}│
        |selected_distros:........  │${selected_distros}│
        |branch_name:.............. │${branch_name}│
        |safe_branch_name:........  │${safe_branch_name}│
        |cmk_version:.............. │${cmk_version}│
        |cmk_version_rc_aware:..... │${cmk_version_rc_aware}│
        |branch_version:........... │${branch_version}│
        |docker_tag:..............  │${docker_tag}│
        |===================================================
        """.stripMargin());

    def relative_job_name = "${branch_base_folder}/builders/test-integration-single-f12less";

    /// avoid failures due to leftover artifacts from prior runs
    sh("rm -rf ${checkout_dir}/test-results");

    def test_stages = all_distros.collectEntries { distro -> [
        ("Test ${distro}") : {
            def stepName = "Test ${distro}";
            def run_condition = distro in selected_distros;

            /// this makes sure the whole parallel thread is marked as skipped
            if (! run_condition){
                Utils.markStageSkippedForConditional(stepName);
            }

            smart_stage(
                name: stepName,
                condition: run_condition,
                raiseOnError: false,
            ) {
                def build_instance = smart_build(
                    // see global-defaults.yml, needs to run in minimal container
                    use_upstream_build: true,
                    relative_job_name: relative_job_name,
                    build_params: [
                        DISTRO: distro,
                        EDITION: EDITION,
                        VERSION: VERSION,
                        CUSTOM_GIT_REF: effective_git_ref,
                    ],
                    build_params_no_check: [
                        CIPARAM_OVERRIDE_BUILD_NODE: CIPARAM_OVERRIDE_BUILD_NODE,
                        CIPARAM_CLEANUP_WORKSPACE: CIPARAM_CLEANUP_WORKSPACE,
                        CIPARAM_BISECT_COMMENT: params.CIPARAM_BISECT_COMMENT,
                    ],
                    no_remove_others: true, // do not delete other files in the dest dir
                    download: false,    // use copyArtifacts to avoid nested directories
                );
                copyArtifacts(
                    projectName: relative_job_name,
                    selector: specific(build_instance.getId()), // buildNumber shall be a string
                    target: "${checkout_dir}/test-results",
                    fingerprintArtifacts: true
                );
            }
        }]
    }

    def image_name = "minimal-alpine-checkmk-ci-master:latest";
    def dockerfile = "${checkout_dir}/buildscripts/scripts/Dockerfile";
    def docker_build_args = "-f ${dockerfile} .";
    def minimal_image = docker.build(image_name, docker_build_args);

    minimal_image.inside(" -v ${checkout_dir}:/checkmk") {
        currentBuild.result = parallel(test_stages).values().every { it } ? "SUCCESS" : "FAILURE";
    }

    stage("Archive / process test reports") {
        dir("${checkout_dir}") {
            show_duration("archiveArtifacts") {
                archiveArtifacts(allowEmptyArchive: true, artifacts: "test-results/**");
            }
            xunit([Custom(
                customXSL: "$JENKINS_HOME/userContent/xunit/JUnit/0.1/pytest-xunit.xsl",
                deleteOutputFiles: true,
                failIfNotNew: false,    // as they are copied from the single tests
                pattern: "**/junit.xml",
                skipNoTestFiles: false,
                stopProcessingIfError: true
            )]);
        }
    }
}

return this;
