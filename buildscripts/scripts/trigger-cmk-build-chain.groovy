#!groovy

/// file: trigger-cmk-build-chain.groovy

import java.time.LocalDate
import org.jenkinsci.plugins.pipeline.modeldefinition.Utils

// groovylint-disable MethodSize
def main() {
    /// make sure the listed parameters are set
    check_job_parameters([
        "CUSTOM_GIT_REF",
        "CIPARAM_OVERRIDE_DOCKER_TAG_BUILD",
        "DISABLE_CMK_DISTRO_PACKAGE_SIGNING",
        "DISABLE_JENKINS_CACHE",
        "FAKE_ARTIFACTS",
        "OVERRIDE_DISTROS",
        "VERSION",

        // test specific parameters
        "RUN_DOCKER_INTEGRATION_TEST",
        "RUN_MULTI_SITE_TEST",
        "RUN_SINGLE_SITE_TEST",
        "RUN_UPDATE_TEST",

        // image specific parameters
        "BUILD_CMK_IMAGE",
        "PUSH_TO_REGISTRY",
        "PUSH_TO_REGISTRY_ONLY",
        "SET_BRANCH_LATEST_TAG",
        "SET_LATEST_TAG",
    ]);

    def versioning = load("${checkout_dir}/buildscripts/scripts/utils/versioning.groovy");

    def safe_branch_name = versioning.safe_branch_name();

    def build_cmk_image_param = params.BUILD_CMK_IMAGE;
    def fake_artifacts = params.FAKE_ARTIFACTS;
    def force_build = params.DISABLE_JENKINS_CACHE == true;
    def run_docker_integration_test_param = params.RUN_DOCKER_INTEGRATION_TEST;
    def run_multi_site_test_param = params.RUN_MULTI_SITE_TEST;
    def run_single_site_test_param = params.RUN_SINGLE_SITE_TEST;
    def run_update_test_param = params.RUN_UPDATE_TEST;
    def version = params.VERSION;

    def base_folder = "${currentBuild.fullProjectName.split('/')[0..-2].join('/')}";
    def edition = JOB_BASE_NAME.split("-")[-1];
    def edition_base_folder = "${base_folder}/nightly-${edition}";
    def use_case = LocalDate.now().getDayOfWeek().toString() in ["SATURDAY", "SUNDAY"] ? "weekly" : "daily";

    def all_editions = ["cloud", "enterprise", "managed", "raw"] ;
    def distros_container_integration_test = ["ubuntu-22.04"];

    def job_parameters_common = [
        CUSTOM_GIT_REF: params.CUSTOM_GIT_REF ?: effective_git_ref,
        DISABLE_CACHE: force_build,
        EDITION: edition,
        FAKE_ARTIFACTS: fake_artifacts,
        VERSION: version,
    ];
    def job_parameters_package = [
        CIPARAM_OVERRIDE_DOCKER_TAG_BUILD: params.CIPARAM_OVERRIDE_DOCKER_TAG_BUILD,
        DISABLE_CMK_DISTRO_PACKAGE_SIGNING: params.DISABLE_CMK_DISTRO_PACKAGE_SIGNING,
        USE_CASE: use_case,

        // image specific parameters
        PUSH_TO_REGISTRY: params.PUSH_TO_REGISTRY,
        PUSH_TO_REGISTRY_ONLY: params.PUSH_TO_REGISTRY_ONLY,
        SET_LATEST_TAG: params.SET_LATEST_TAG,
        SET_BRANCH_LATEST_TAG: params.SET_BRANCH_LATEST_TAG,
    ];
    def job_parameters_no_check = [
        CIPARAM_OVERRIDE_BUILD_NODE: params.CIPARAM_OVERRIDE_BUILD_NODE,
        CIPARAM_CLEANUP_WORKSPACE: params.CIPARAM_CLEANUP_WORKSPACE,
        CIPARAM_BISECT_COMMENT: params.CIPARAM_BISECT_COMMENT,
    ];

    /// Might also be taken from editions.yml - there we also have "cloud" and "community" but
    /// AFAIK there is no way to extract the editions we want to test generically, so we
    /// hard-code these:
    def all_distros = [];
    def selected_distros = [];
    def timeOffsetForOrder = 0;

    // TODO we should take this list from a single source of truth
    assert edition in all_editions : (
        "Do not know edition '${edition}' extracted from ${JOB_BASE_NAME}");

    inside_container_minimal(safe_branch_name: safe_branch_name) {
        // run everything requiring python in this container
        all_distros = versioning.get_distros(override: "all");
        selected_distros = versioning.get_distros(
            edition: edition,
            use_case: use_case,
            override: params.OVERRIDE_DISTROS);
    }

    print(
        """
        |===== CONFIGURATION ===============================
        |all_distros:........................ │${all_distros}│
        |edition:............................ │${edition}│
        |edition_base_folder:................ │${edition_base_folder}│
        |fake_artifacts:..................... │${fake_artifacts}│
        |force_build:........................ │${force_build}│
        |run_docker_integration_test_param:.. │${run_docker_integration_test_param}│
        |run_multi_site_test_param:.......... │${run_multi_site_test_param}│
        |run_single_site_test_param:......... │${run_single_site_test_param}│
        |run_update_test_param:.............. │${run_update_test_param}│
        |safe_branch_name:................... │${safe_branch_name}│
        |selected_distros:................... │${selected_distros}│
        |use_case:........................... │${use_case}│
        |===================================================
        """.stripMargin());

    // use smart_stage to capture build result, but continue with next steps
    // this runs the consecutive stages and jobs in any case which makes it easier to re-run or fix only those distros with the next run
    // which actually failed without triggering all jobs for all but the failing distros
    inside_container_minimal(safe_branch_name: safe_branch_name) {
        def parallel_stages = all_distros.collectEntries { distro ->
            [("${distro}") : {
                sleep(1 * timeOffsetForOrder++);
                def run_condition = distro in selected_distros;
                // groovylint-disable-next-line UnusedVariable
                def build_instance = null;

                /// this makes sure the whole parallel thread is marked as skipped
                if (! run_condition) {
                    Utils.markStageSkippedForConditional("${distro}");
                }

                def build_cmk_image = [
                    build_cmk_image_param,
                    distro in distros_container_integration_test,
                ].every { it };
                def run_docker_integration_test = [
                    run_docker_integration_test_param,
                    !(edition in ["managed", "cloud"]),
                    distro in distros_container_integration_test,
                ].every { it };
                def run_multi_site_test = [
                    run_multi_site_test_param,
                    !(edition in ["cloud",]),
                ].every { it };

                def job_parameters_testing = [
                    BUILD_CMK_IMAGE: build_cmk_image,

                    RUN_DOCKER_INTEGRATION_TEST: run_docker_integration_test,
                    RUN_MULTI_SITE_TEST: run_multi_site_test,
                    RUN_SINGLE_SITE_TEST: run_single_site_test_param,
                    RUN_UPDATE_TEST: run_update_test_param,
                ];
                print("job_parameters_testing: ${job_parameters_testing}");

                smart_stage(
                    name: "${distro}",
                    condition: run_condition,
                    raiseOnError: false,
                ) {
                    build_instance = smart_build(
                        // see global-defaults.yml, needs to run in minimal container
                        use_upstream_build: true,
                        force_build: force_build,
                        relative_job_name: "${edition_base_folder}/trigger-distro-chain",
                        build_params: job_parameters_common + job_parameters_package + [DISTRO: distro,] + job_parameters_testing,
                        build_params_no_check: job_parameters_no_check,
                        download: false,
                    );
                }
            }]
        }

        currentBuild.result = parallel(parallel_stages).values().every { it } ? "SUCCESS" : "FAILURE";
    }
}

return this;
