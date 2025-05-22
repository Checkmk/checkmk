#!groovy

/// file: test-gerrit.groovy

import org.jenkinsci.plugins.pipeline.modeldefinition.Utils

def main() {
    def package_helper = load("${checkout_dir}/buildscripts/scripts/utils/package_helper.groovy");
    def test_gerrit_helper = load("${checkout_dir}/buildscripts/scripts/utils/gerrit_stages.groovy");
    def test_jenkins_helper = load("${checkout_dir}/buildscripts/scripts/utils/test_helper.groovy");
    def versioning = load("${checkout_dir}/buildscripts/scripts/utils/versioning.groovy");

    def result_dir = "${checkout_dir}/results";
    def time_job_started = new Date();
    def time_stage_started = time_job_started;
    def safe_branch_name = versioning.safe_branch_name();

    def branch_base_folder = package_helper.branch_base_folder(with_testing_prefix: true);
    def stage_info = null;

    // do not touch the status page during the build, it might be overwritten/dropped by another parallel step
    // add elements to this mapping to render them at the end
    def analyse_mapping = [:];

    print(
        """
        |===== CONFIGURATION ===============================
        |GERRIT_PATCHSET_REVISION:.(global)  │${GERRIT_PATCHSET_REVISION}│
        |GERRIT_CHANGE_SUBJECT:....(global)  │${GERRIT_CHANGE_SUBJECT}│
        |GERRIT_BRANCH:............(global)  │${GERRIT_BRANCH}│
        |===================================================
        """.stripMargin());

    withCredentials([
        usernamePassword(
            credentialsId: 'nexus',
            passwordVariable: 'DOCKER_PASSPHRASE',
            usernameVariable: 'DOCKER_USERNAME')]) {
        sh('echo  "${DOCKER_PASSPHRASE}" | docker login "${DOCKER_REGISTRY}" -u "${DOCKER_USERNAME}" --password-stdin');
    }

    /// Add description to the build
    test_gerrit_helper.desc_init();
    test_gerrit_helper.desc_add_line("${GERRIT_CHANGE_SUBJECT}");
    test_gerrit_helper.desc_add_table(['Stage', 'Duration', 'Status', 'Parsed results', 'Result files']);

    stage("Prepare workspace") {
        dir("${checkout_dir}") {
            sh("rm -rf ${result_dir}; mkdir ${result_dir}");
        }
    }

    stage("Create stages") {
        dir("${checkout_dir}") {
            inside_container_minimal(safe_branch_name: safe_branch_name) {
                /// Generate list of stages to be added - save them locally for reference
                sh("""python buildscripts/scripts/validate_changes.py \
                      --env "RESULTS=${result_dir}" \
                      --env "WORKSPACE=${checkout_dir}" \
                      --env "PATCHSET_REVISION=${GERRIT_PATCHSET_REVISION}" \
                      --write-file=${result_dir}/stages.json \
                      buildscripts/scripts/stages.yml
                """);
            }
        }

        time_stage_started = new Date();
        analyse_mapping["Preparation"] = [
            stepName: "Preparation",
            duration: groovy.time.TimeCategory.minus(new Date(), time_job_started),
            status: "success",
        ];
        stage_info = load_json("${result_dir}/stages.json");
    }

    def stepsForParallel = stage_info.STAGES.collectEntries { item -> [
        ("Test ${item.NAME}") : {
            def stepName = "Test ${item.NAME}";
            def run_condition = !item.SKIPPED;
            def build_instance = null;

            /// this makes sure the whole parallel thread is marked as skipped
            if (! run_condition){
                Utils.markStageSkippedForConditional(stepName);
                return true;
            } else {
                // can not use join(",") as "," are not supported by ci-artifacts
                def env_var_list_str = "";
                def sec_var_list_str = "";
                if (item.ENV_VAR_LIST) {
                    env_var_list_str = item.ENV_VAR_LIST.join("#").replace("${checkout_dir}", "JOB_SPECIFIC_SPACE_PLACEHOLDER");
                }
                if (item.SEC_VAR_LIST) {
                    sec_var_list_str = item.SEC_VAR_LIST.join("#");
                }
                def independent_command = item.COMMAND.replace("${checkout_dir}", "JOB_SPECIFIC_SPACE_PLACEHOLDER");
                def relative_job_name = "${branch_base_folder}/cv/test-gerrit-single"

                smart_stage(
                    name: stepName,
                    condition: run_condition,
                    raiseOnError: false,
                ) {
                    // build_params has to be a local variable of a stage to avoid re-using it from other stages
                    def build_params = [:];

                    switch("${item.NAME}") {
                        case "Enforced package build":
                            relative_job_name = "${branch_base_folder}/builders/build-cmk-distro-package";
                            build_params << [
                                CUSTOM_GIT_REF: GERRIT_PATCHSET_REVISION,
                                DISTRO: "ubuntu-22.04",
                                EDITION: "enterprise",
                            ];
                            break;
                        default:
                            relative_job_name = "${branch_base_folder}/cv/test-gerrit-single";
                            build_params << [
                                CUSTOM_GIT_REF: GERRIT_PATCHSET_REVISION,
                                CIPARAM_NAME: item.NAME,
                                CIPARAM_DIR: item.DIR,
                                CIPARAM_ENV_VARS: item.ENV_VARS,
                                CIPARAM_ENV_VAR_LIST_STR: env_var_list_str,
                                CIPARAM_SEC_VAR_LIST_STR: sec_var_list_str,
                                CIPARAM_GIT_FETCH_TAGS: item.GIT_FETCH_TAGS,
                                CIPARAM_GIT_FETCH_NOTES: item.GIT_FETCH_NOTES,
                                CIPARAM_COMMAND: independent_command,
                                CIPARAM_RESULT_CHECK_FILE_PATTERN: item.RESULT_CHECK_FILE_PATTERN,
                                CIPARAM_BAZEL_LOCKS_AMOUNT: item.BAZEL_LOCKS_AMOUNT,
                            ];
                            break;
                    }
                    // preparing the mapping entry here before the smart_build call
                    // ensures the stage is always listed in the job overview independant of the result
                    // or failures during execution or similar
                    analyse_mapping["${item.NAME}"] = [
                        stepName: item.NAME,
                        duration: groovy.time.TimeCategory.minus(new Date(), time_stage_started),
                        status: "failure",
                    ];

                    build_instance = smart_build(
                        // see global-defaults.yml, needs to run in minimal container
                        use_upstream_build: true,
                        relative_job_name: relative_job_name,
                        build_params: build_params,
                        build_params_no_check: [
                            CIPARAM_OVERRIDE_BUILD_NODE: params.CIPARAM_OVERRIDE_BUILD_NODE,
                            CIPARAM_CLEANUP_WORKSPACE: params.CIPARAM_CLEANUP_WORKSPACE,
                            CIPARAM_BISECT_COMMENT: params.CIPARAM_BISECT_COMMENT,
                        ],
                        no_remove_others: true, // do not delete other files in the dest dir
                        download: false,    // use copyArtifacts to avoid nested directories
                        print_html: false,  // do not update Jenkins Job page with infos like upstream build URLs or similar
                    );

                    analyse_mapping["${item.NAME}"] = [
                        stepName: item.NAME,
                        duration: groovy.time.TimeCategory.minus(new Date(), time_stage_started),
                        status: "${build_instance.getResult()}".toLowerCase(),
                        triggered_build_url: build_instance.getAbsoluteUrl(),
                    ];
                }

                smart_stage(
                    name: "Copy artifacts",
                    condition: run_condition && build_instance && item.RESULT_CHECK_FILE_PATTERN,
                    raiseOnError: false,
                ) {
                    copyArtifacts(
                        projectName: relative_job_name,
                        selector: specific(build_instance.getId()),
                        target: "${checkout_dir}",
                        fingerprintArtifacts: true,
                    )

                    analyse_mapping["${item.NAME}"] << [
                        pattern: "${item.RESULT_CHECK_FILE_PATTERN}",
                    ];
                }

                smart_stage(
                    name: "Analyse issues",
                    condition: run_condition && build_instance && item.RESULT_CHECK_FILE_PATTERN && item.RESULT_CHECK_TYPE,
                    raiseOnError: false,
                ) {
                    analyse_mapping["${item.NAME}"] << [
                        unique_parser_name: "${item.RESULT_CHECK_FILE_PATTERN}".replaceAll("""([^A-Za-z0-9\\-\\_]+)""", "-"),
                    ];

                    // ensure the parser and publisher are able to find the files
                    dir("${checkout_dir}") {
                        // as issue analysis can not be run in parallel, do it sequential, old school
                        // https://groups.google.com/g/jenkinsci-dev/c/vEHMw4kp6iQ
                        // https://stackoverflow.com/questions/61428125/how-to-use-the-three-steps-of-jenkins-warnings-next-generation-plugin-properly
                        def issues = test_jenkins_helper.analyse_issues(
                            item.RESULT_CHECK_TYPE,
                            item.RESULT_CHECK_FILE_PATTERN,
                            false,  // do not run analysis as dedicated stage
                        );

                        publishIssues(
                            issues: issues,
                            name: "${item.NAME}",
                            // Only characters, digits, dashes and underscores allowed
                            // ID must match the regex \p{Alnum}[\p{Alnum}-_]*).
                            id: "${item.RESULT_CHECK_FILE_PATTERN}".replaceAll("""([^A-Za-z0-9\\-\\_]+)""", "-"),
                            trendChartType: "TOOLS_ONLY",
                            qualityGates: [[
                                threshold: 1,
                                type: "TOTAL",
                                unstable: false,
                            ]],
                        );
                    }
                }
            }
        }]
    }

    inside_container_minimal(safe_branch_name: safe_branch_name) {
        def results_of_parallel = parallel(stepsForParallel);
        currentBuild.result = results_of_parallel.values().every { it } ? "SUCCESS" : "FAILURE";
    }

    stage("Render job page") {
        analyse_mapping.each { entry ->
            test_gerrit_helper.desc_add_status_row_gerrit(entry.value);
        };
        test_gerrit_helper.desc_add_table_bottom();
    }

    stage("Analyse Issues") {
        dir("${checkout_dir}") {
            xunit([
                Custom(
                    customXSL: "$JENKINS_HOME/userContent/xunit/JUnit/0.1/pytest-xunit.xsl",
                    deleteOutputFiles: false,
                    failIfNotNew: false,    // as they are copied from the single tests
                    pattern: "results/*junit.xml",
                    skipNoTestFiles: true,
                    stopProcessingIfError: true,
                )
            ]);
        }
    }

    stage("Archive artifacts") {
        dir("${checkout_dir}") {
            show_duration("archiveArtifacts") {
                archiveArtifacts(allowEmptyArchive: true, artifacts: 'results/**');
            }
        }
    }
}

return this;
