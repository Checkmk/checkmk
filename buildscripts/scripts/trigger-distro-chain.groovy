#!groovy

/// file: trigger-distro-chain.groovy

import org.jenkinsci.plugins.pipeline.modeldefinition.Utils

// groovylint-disable MethodSize
void main() {
    /// make sure the listed parameters are set
    check_job_parameters([
        "CUSTOM_GIT_REF",
        "CIPARAM_OVERRIDE_DOCKER_TAG_BUILD",
        "DISABLE_CMK_DISTRO_PACKAGE_SIGNING",
        "DISABLE_JENKINS_CACHE",
        "DISTRO",
        "EDITION",
        "FAKE_ARTIFACTS",
        "RUN_COMPONENT_MK_ORACLE_TEST",
        "RUN_DOCKER_INTEGRATION_TEST",
        "RUN_MULTI_SITE_TEST",
        "RUN_SINGLE_SITE_TEST",
        "RUN_SYSTEM_AGENT_UPDATE_TEST",
        "RUN_UPDATE_TEST",
        "USE_CASE",
        "VERSION",
        // image specific parameters
        "BUILD_CMK_IMAGE",
        "PUSH_TO_REGISTRY",
        "PUSH_TO_REGISTRY_ONLY",
        "SET_BRANCH_LATEST_TAG",
        "SET_LATEST_TAG",
    ]);

    def package_helper = load("${checkout_dir}/buildscripts/scripts/utils/package_helper.groovy");
    def versioning = load("${checkout_dir}/buildscripts/scripts/utils/versioning.groovy");

    def branch_base_folder = package_helper.branch_base_folder(true);
    def safe_branch_name = versioning.safe_branch_name();

    def build_cmk_image = params.BUILD_CMK_IMAGE;
    def distro = params.DISTRO;
    def edition = params.EDITION;
    def fake_artifacts = params.FAKE_ARTIFACTS;
    def force_build = params.DISABLE_JENKINS_CACHE == true;
    def run_component_mk_oracle_test = params.RUN_COMPONENT_MK_ORACLE_TEST;
    def run_docker_integration_test = params.RUN_DOCKER_INTEGRATION_TEST;
    def run_multi_site_test = params.RUN_MULTI_SITE_TEST;
    def run_single_site_test = params.RUN_SINGLE_SITE_TEST;
    def run_system_agent_update_test = params.RUN_SYSTEM_AGENT_UPDATE_TEST;
    def run_update_test = params.RUN_UPDATE_TEST;
    def use_case = params.USE_CASE;
    def version = params.VERSION;

    def builders_base_folder = "${branch_base_folder}/builders";
    def distros_component_mk_oracle_test = ["almalinux-8"];
    def distros_container_integration_test = ["ubuntu-22.04"];
    def distros_system_agent_update_test = ["ubuntu-24.04", "almalinux-10"];
    def edition_base_folder = "${branch_base_folder}/nightly-${edition}";

    def job_parameters_common = [
        CUSTOM_GIT_REF: params.CUSTOM_GIT_REF ?: effective_git_ref,
        DISABLE_CACHE: force_build,
        DISTRO: distro,
        EDITION: edition,
        FAKE_ARTIFACTS: fake_artifacts,
        VERSION: version,
    ];
    def job_parameters_image = [
        PUSH_TO_REGISTRY: params.PUSH_TO_REGISTRY,
        PUSH_TO_REGISTRY_ONLY: params.PUSH_TO_REGISTRY_ONLY,
        SET_LATEST_TAG: params.SET_LATEST_TAG,
        SET_BRANCH_LATEST_TAG: params.SET_BRANCH_LATEST_TAG,
    ];
    def job_parameters_packages = job_parameters_common + [
        CIPARAM_OVERRIDE_DOCKER_TAG_BUILD: params.CIPARAM_OVERRIDE_DOCKER_TAG_BUILD,
        DISABLE_CMK_DISTRO_PACKAGE_SIGNING: params.DISABLE_CMK_DISTRO_PACKAGE_SIGNING,
        USE_CASE: use_case,
    ];
    def job_parameters_no_check = [
        CIPARAM_OVERRIDE_BUILD_NODE: params.CIPARAM_OVERRIDE_BUILD_NODE,
        CIPARAM_CLEANUP_WORKSPACE: params.CIPARAM_CLEANUP_WORKSPACE,
        CIPARAM_BISECT_COMMENT: params.CIPARAM_BISECT_COMMENT,
    ];
    def success = true;

    run_docker_integration_test = [
        run_docker_integration_test,
        distro in distros_container_integration_test,
    ].every { it };
    run_component_mk_oracle_test = [
        run_component_mk_oracle_test,
        distro in distros_component_mk_oracle_test,
        edition == "ultimatemt",
    ].every { it };
    run_system_agent_update_test = [
        run_system_agent_update_test,
        distro in distros_system_agent_update_test,
        edition == "pro",
    ].every { it };

    print(
        """
        |===== CONFIGURATION ===============================
        |build_cmk_image:.............. │${build_cmk_image}│
        |distro:....................... │${distro}│
        |edition:...................... │${edition}│
        |fake_artifacts:............... │${fake_artifacts}│
        |force_build:.................. │${force_build}│
        |run_component_mk_oracle_test:. │${run_component_mk_oracle_test}│
        |run_docker_integration_test:.. │${run_docker_integration_test}│
        |run_multi_site_test:.......... │${run_multi_site_test}│
        |run_single_site_test:......... │${run_single_site_test}│
        |run_system_agent_update_test:. │${run_system_agent_update_test}│
        |run_update_test:.............. │${run_update_test}│
        |safe_branch_name:............. │${safe_branch_name}│
        |use_case:..................... │${use_case}│
        |===================================================
        """.stripMargin());

    // use smart_stage to capture build result, but continue with next steps
    // this runs the consecutive stages and jobs in any case which makes it easier to re-run or fix only those distros with the next run
    // which actually failed without triggering all jobs for all but the failing distros
    inside_container_minimal(safe_branch_name: safe_branch_name) {
        smart_stage(
            name: "Build Package",
            condition: true,
            raiseOnError: true,
        ) {
            smart_build(
                use_upstream_build: true,
                force_build: force_build,
                relative_job_name: "${builders_base_folder}/trigger-cmk-distro-package",
                build_params: job_parameters_packages,
                build_params_no_check: job_parameters_no_check,
                download: false,
            );
        }

        smart_stage(
            name: "Build CMK IMAGE",
            condition: build_cmk_image && currentBuild.result != "FAILURE",
            raiseOnError: false,
        ) {
            smart_build(
                use_upstream_build: true,
                force_build: force_build,
                relative_job_name: "${edition_base_folder}/build-cmk-image",
                build_params: job_parameters_common + job_parameters_image,
                build_params_no_check: job_parameters_no_check,
                download: false,
            );
        }

        def parallel_stages = [
            "test-component-mk-oracle": {
                smart_stage(
                    name: "Component tests for mk-oracle",
                    condition: run_component_mk_oracle_test,
                    raiseOnError: false,
                ) {
                    smart_build(
                        use_upstream_build: true,
                        force_build: force_build,
                        relative_job_name: "${builders_base_folder}/test-component-mk-oracle",
                        build_params: [
                            EDITION: params.EDITION,
                            VERSION: params.VERSION,
                            DISABLE_CACHE: params.DISABLE_CACHE,
                        ],
                        build_params_no_check: job_parameters_no_check,
                        download: false,
                    );
                }[0]
            },
            "test-integration-docker": {
                smart_stage(
                    name: "Integration Test for Docker Container",
                    condition: run_docker_integration_test,
                    raiseOnError: false,
                ) {
                    smart_build(
                        use_upstream_build: true,
                        force_build: force_build,
                        relative_job_name: "${edition_base_folder}/test-integration-docker",
                        build_params: job_parameters_packages,
                        build_params_no_check: job_parameters_no_check,
                        download: false,
                    );
                }[0]
            },
            "test-system-agent-updates": {
                smart_stage(
                    name: "Agent update test",
                    condition: run_system_agent_update_test,
                    raiseOnError: false,
                ) {
                    smart_build(
                        use_upstream_build: true,
                        force_build: force_build,
                        relative_job_name: "${builders_base_folder}/test-system-agent-updates",
                        build_params: job_parameters_packages,
                        build_params_no_check: job_parameters_no_check,
                        download: false,
                    );
                }[0]
            },
            "test-system-multisite": {
                smart_stage(
                    name: "Composition Test for Packages",
                    condition: run_multi_site_test,
                    raiseOnError: false,
                ) {
                    smart_build(
                        use_upstream_build: true,
                        force_build: force_build,
                        relative_job_name: "${builders_base_folder}/test-system-multisite-single",
                        build_params: job_parameters_packages,
                        build_params_no_check: job_parameters_no_check,
                        download: false,
                    );
                }[0]
            },
            "test-system-singlesite": {
                smart_stage(
                    name: "Integration Test for Packages",
                    condition: run_single_site_test,
                    raiseOnError: false,
                ) {
                    smart_build(
                        use_upstream_build: true,
                        force_build: force_build,
                        relative_job_name: "${builders_base_folder}/test-system-singlesite-single",
                        build_params: job_parameters_packages,
                        build_params_no_check: job_parameters_no_check,
                        download: false,
                    );
                }[0]
            },
            "test-system-update": {
                smart_stage(
                    name: "Update Test",
                    condition: run_update_test,
                    raiseOnError: false,
                ) {
                    smart_build(
                        use_upstream_build: true,
                        force_build: force_build,
                        relative_job_name: "${builders_base_folder}/test-system-update-single",
                        build_params: job_parameters_packages,
                        build_params_no_check: job_parameters_no_check,
                        download: false,
                    );
                }[0]
            },
        ];

        // use the negative path as currentBuild might not be set yet if everything passed so far
        if (currentBuild.result != "FAILURE") {
            currentBuild.result = parallel(parallel_stages).values().every { it } ? "SUCCESS" : "FAILURE";
        } else {
            /// this makes sure the whole parallel thread is marked as skipped
            Utils.markStageSkippedForConditional("Package or image build error occured");
        }

        // this job is responsible to upload CMK package artifacts to remote locations
        success &= smart_stage(
            name: "Upload package",
            condition: currentBuild.result != "FAILURE",
            raiseOnError: false,
        ) {
            smart_build(
                use_upstream_build: true,
                force_build: force_build,
                relative_job_name: "${edition_base_folder}/build-cmk-deliverables",
                build_params: job_parameters_packages + [
                    OVERRIDE_DISTROS: distro,
                ],
                build_params_no_check: job_parameters_no_check,
                download: false,
            );
        }[0]

        currentBuild.result = success ? "SUCCESS" : "FAILURE";
    }
}

return this;
