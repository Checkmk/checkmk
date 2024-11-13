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
    def parallel_stages_states = [];
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
                raiseOnError: false,
            ) {
                def this_exit_successfully = false;
                def job = build(
                    job: relative_job_name,
                    propagate: false,   // do not raise here, continue, get status via result property later
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
                println("job result is: ${job.result}");
                // be really really sure if it is a success
                if (job.result == "SUCCESS") {
                    this_exit_successfully = true;
                } else {
                    error("${distro.NAME} failed");
                }
                parallel_stages_states.add(this_exit_successfully);
            }
        }
    }

    stage('Run composition tests') {
        parallel build_for_parallel;
    }

    println("All stages results: ${parallel_stages_states}");
    all_true = parallel_stages_states.every { it == true } == true;
    currentBuild.result = all_true ? "SUCCESS" : "FAILED";
}

return this;
