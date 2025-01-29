#!groovy

/// file: test-composition.groovy

/// Run composition tests

import org.jenkinsci.plugins.pipeline.modeldefinition.Utils

def main() {
    check_job_parameters([
        "EDITION",
        "VERSION",
        "OVERRIDE_DISTROS",
        "CIPARAM_OVERRIDE_DOCKER_TAG_BUILD",
        "USE_CASE",
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
        CIPARAM_OVERRIDE_DOCKER_TAG_BUILD,  // 'build tag'
        safe_branch_name,                   // 'branch' returns '<BRANCH>-latest'
    );

    currentBuild.description += (
        """
        |Run composition tests for<br>
        |VERSION: ${VERSION}<br>
        |EDITION: ${EDITION}<br>
        |selected_distros: ${selected_distros}<br>
        """.stripMargin());

    print(
        """
        |===== CONFIGURATION ===============================
        |selected_distros:........  │${selected_distros}│
        |branch_name:.............. │${branch_name}│
        |safe_branch_name:........  │${safe_branch_name}│
        |cmk_version:.............. │${cmk_version}│
        |cmk_version_rc_aware:..... │${cmk_version_rc_aware}│
        |branch_version:........... │${branch_version}│
        |docker_tag:..............  │${docker_tag}│
        |===================================================
        """.stripMargin());

    def relative_job_name = "${branch_base_folder}/builders/test-composition-single-f12less";

    /// avoid failures due to leftover artifacts from prior runs
    sh("rm -rf ${checkout_dir}/test-results");

    def test_stages = all_distros.collectEntries { distro -> [
        ("Test ${distro}") : {
            def run_condition = distro in selected_distros;

            /// this makes sure the whole parallel thread is marked as skipped
            if (! run_condition){
                Utils.markStageSkippedForConditional("Test ${distro}");
            }

            smart_stage(
                name: "Test ${distro}",
                condition: run_condition,
                raiseOnError: false,
            ) {
                def build_instance = smart_build(
                    job: relative_job_name,
                    parameters: [
                        stringParam(name: "DISTRO", value: distro),
                        stringParam(name: "EDITION", value: EDITION),
                        stringParam(name: "VERSION", value: VERSION),
                        stringParam(name: "DOCKER_TAG", value: docker_tag),
                        stringParam(name: "CUSTOM_GIT_REF", value: effective_git_ref),
                        stringParam(name: "CIPARAM_OVERRIDE_BUILD_NODE", value: CIPARAM_OVERRIDE_BUILD_NODE),
                        stringParam(name: "CIPARAM_CLEANUP_WORKSPACE", value: CIPARAM_CLEANUP_WORKSPACE),
                        stringParam(name: "CIPARAM_BISECT_COMMENT", value: params.CIPARAM_BISECT_COMMENT),
                    ],
                );
                copyArtifacts(
                    projectName: build_instance.getFullProjectName(),
                    selector: specific(build_instance.getId()), // buildNumber shall be a string
                    target: "${checkout_dir}/test-results",
                    fingerprintArtifacts: true
                );
                return build_instance.getResult();
            }
        }]
    }

    currentBuild.result = parallel(test_stages).values().every { it } ? "SUCCESS" : "FAILURE";

    stage("Archive / process test reports") {
        dir("${checkout_dir}") {
            show_duration("archiveArtifacts") {
                archiveArtifacts(allowEmptyArchive: true, artifacts: "test-results/**");
            }
            xunit([Custom(
                customXSL: "$JENKINS_HOME/userContent/xunit/JUnit/0.1/pytest-xunit.xsl",
                deleteOutputFiles: true,
                failIfNotNew: true,
                pattern: "**/junit.xml",
                skipNoTestFiles: false,
                stopProcessingIfError: true
            )]);
        }
    }
}

return this;
