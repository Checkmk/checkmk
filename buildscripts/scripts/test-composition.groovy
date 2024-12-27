#!groovy

/// file: test-composition.groovy

/// Run composition tests

/// Jenkins artifacts: ???
/// Other artifacts: ???
/// Depends on: ???

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
    def testing_helper = load("${checkout_dir}/buildscripts/scripts/utils/integration.groovy");
    def test_jenkins_helper = load("${checkout_dir}/buildscripts/scripts/utils/test_helper.groovy");

    // TODO: we should always use USE_CASE directly from the job parameters
    def use_case = (USE_CASE == "fips") ? USE_CASE : "daily_tests"
    test_jenkins_helper.assert_fips_testing(use_case, NODE_LABELS);
    def all_distros = versioning.get_distros(override: "all");
    def distros_under_test = versioning.get_distros(edition: EDITION, use_case: use_case, override: OVERRIDE_DISTROS);

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
        |distros: ${distros_under_test}<br>
        """.stripMargin());

    print(
        """
        |===== CONFIGURATION ===============================
        |distros:...................│${distros_under_test}│
        |branch_name:.............. │${branch_name}│
        |safe_branch_name:......... │${safe_branch_name}│
        |cmk_version:.............. │${cmk_version}│
        |cmk_version_rc_aware:..... │${cmk_version_rc_aware}│
        |branch_version:........... │${branch_version}│
        |docker_tag:............... │${docker_tag}│
        |checkout_dir:............. │${checkout_dir}│
        |===================================================
        """.stripMargin());

    def build_for_parallel = [:];
    def base_folder = "${currentBuild.fullProjectName.split('/')[0..-3].join('/')}";
    def relative_job_name = "${base_folder}/builders/test-composition-single-f12less";

    all_distros.each { item ->
        def distro = item;
        def stepName = "Composition test for ${distro}";

        build_for_parallel[stepName] = { ->
            def run_condition = distro in distros_under_test;
            println("Should ${distro} be tested? ${run_condition}");

            /// this makes sure the whole parallel thread is marked as skipped
            if (! run_condition){
                Utils.markStageSkippedForConditional(stepName);
            }

            smart_stage(
                name: stepName,
                condition: run_condition,
                raiseOnError: true,
            ) {
                def job = build(
                    job: relative_job_name,
                    propagate: false,  // Not raise any errors
                    parameters: [
                        string(name: "DISTRO", value: distro),
                        string(name: "EDITION", value: EDITION),
                        string(name: "VERSION", value: VERSION),
                        string(name: "DOCKER_TAG", value: docker_tag),
                        string(name: "CUSTOM_GIT_REF", value: CUSTOM_GIT_REF),
                        string(name: "CIPARAM_OVERRIDE_BUILD_NODE", value: CIPARAM_OVERRIDE_BUILD_NODE),
                        string(name: "CIPARAM_CLEANUP_WORKSPACE", value: CIPARAM_CLEANUP_WORKSPACE),
                    ],
                );

                copyArtifacts(
                    projectName: relative_job_name,
                    selector: specific(job.getId()), // buildNumber shall be a string
                    target: "${checkout_dir}/test-results",
                    fingerprintArtifacts: true
                );

                if (job.result != 'SUCCESS') {
                    raise("${relative_job_name} failed with result: ${job.result}");
                }
            }
        }
    }

    stage('Run composition tests') {
        parallel build_for_parallel;
    }

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
