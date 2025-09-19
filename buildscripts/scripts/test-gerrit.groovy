#!groovy

/// file: test-gerrit.groovy

import org.jenkinsci.plugins.pipeline.modeldefinition.Utils

def main_parallel() {
    def package_helper = load("${checkout_dir}/buildscripts/scripts/utils/package_helper.groovy");
    def test_jenkins_helper = load("${checkout_dir}/buildscripts/scripts/utils/test_helper.groovy");
    def versioning = load("${checkout_dir}/buildscripts/scripts/utils/versioning.groovy");

    def result_dir = "${checkout_dir}/results";
    def time_job_started = new Date();
    def time_stage_started = time_job_started;
    def safe_branch_name = versioning.safe_branch_name();

    def branch_base_folder = package_helper.branch_base_folder(with_testing_prefix: true);
    def stage_info = null;

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

    def current_description = currentBuild.description;

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
        update_result_table(current_description, analyse_mapping);
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
                    def build_params = [:];

                    switch("${item.NAME}") {
                        case "Enforced package build":
                            relative_job_name = "${branch_base_folder}/builders/build-cmk-distro-package";
                            build_params << [
                                CUSTOM_GIT_REF: GERRIT_PATCHSET_REVISION,
                                DISTRO: "ubuntu-24.04",
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

                    analyse_mapping["${item.NAME}"] = [
                        stepName: item.NAME,
                        duration: groovy.time.TimeCategory.minus(new Date(), time_stage_started),
                        status: "ongoing",
                    ];

                    try {
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
                    } finally {
                        analyse_mapping["${item.NAME}"] = [
                            stepName: item.NAME,
                            duration: groovy.time.TimeCategory.minus(new Date(), time_stage_started),
                            status: "${build_instance.getResult()}".toLowerCase(),
                            triggered_build_url: build_instance.getAbsoluteUrl(),
                            test_result_path: item.JENKINS_TEST_RESULT_PATH,
                        ];
                    }
                    update_result_table(current_description, analyse_mapping);
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
                    );

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
                        if (item.RESULT_CHECK_TYPE == "JUNIT") {
                            dir("${checkout_dir}") {
                                try {
                                    xunit(
                                        checksName: item.NAME,
                                        tools: [
                                            Custom(
                                                customXSL: "$JENKINS_HOME/userContent/xunit/JUnit/0.1/pytest-xunit.xsl",
                                                deleteOutputFiles: false,
                                                failIfNotNew: false, // as they are copied from the single tests
                                                pattern: item.RESULT_CHECK_FILE_PATTERN,
                                                skipNoTestFiles: true,
                                                stopProcessingIfError: true,
                                            )
                                        ]
                                    );
                                } catch (Exception exc) {
                                    print("ERROR: ran into exception while running xunit() for ${item.NAME}: ${exc}");
                                }
                            }
                        }
                    }
                }
            }
        }]
    /// add a dummy step which populates the result table before the first real step has finished
    } + ["CV internal: initial result table population": {sleep(2); update_result_table(current_description, analyse_mapping);}]

    inside_container_minimal(safe_branch_name: safe_branch_name) {
        def results_of_parallel = parallel(stepsForParallel);
        currentBuild.result = results_of_parallel.values().every { it } ? "SUCCESS" : "FAILURE";
    }

    stage("Archive artifacts") {
        dir("${checkout_dir}") {
            show_duration("archiveArtifacts") {
                archiveArtifacts(allowEmptyArchive: true, artifacts: 'results/**');
            }
        }
    }
}

def main_sequential() {
    def test_gerrit_helper = load("${checkout_dir}/buildscripts/scripts/utils/gerrit_stages.groovy");
    // no `def` - must be global
    test_jenkins_helper = load("${checkout_dir}/buildscripts/scripts/utils/test_helper.groovy");
    def versioning = load("${checkout_dir}/buildscripts/scripts/utils/versioning.groovy");

    def result_dir = "${checkout_dir}/results";
    def time_job_started = new Date();
    def time_stage_started = time_job_started;
    def safe_branch_name = versioning.safe_branch_name();

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
    test_gerrit_helper.desc_add_table();
    test_gerrit_helper.desc_add_row('Stage', 'Duration', 'Status', 'Result files');

    stage("Prepare workspace") {
        dir("${checkout_dir}") {

            inside_container() {
                sh("buildscripts/scripts/ensure-workspace-integrity");
            }
            sh("rm -rf ${result_dir}; mkdir ${result_dir}");
        }
    }
    try {

        dir("${checkout_dir}") {
            stage("Create stages") {
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
                time_stage_started = new Date();
            }
            test_gerrit_helper.desc_add_status_row("Preparation",
                groovy.time.TimeCategory.minus(new Date(), time_job_started), 0, '--');
            def stage_info = load_json("${result_dir}/stages.json");
            def allStagesPassed = true;
            def thisStagePassed = true;
            // privileged/set_docker_group_id aka mounting the docker is needed for agent plugin tests: they do docker in docker
            inside_container(privileged: true, set_docker_group_id: true) {
                stage_info.STAGES.each { item ->
                    (thisStagePassed, thisIssues) = test_gerrit_helper.create_stage(item, time_stage_started);
                    allStagesPassed = thisStagePassed && allStagesPassed;
                    if (thisIssues && !thisStagePassed) {
                        stage("Analyse Issues") {
                            thisIssues.each { issue ->
                                publishIssues(
                                    issues: [issue],
                                    name: "${item.NAME}",
                                    // Only characters, digits, dashes and underscores allowed
                                    // ID must match the regex \p{Alnum}[\p{Alnum}-_]*).
                                    id: "${item.RESULT_CHECK_FILE_PATTERN}".replaceAll("""([^A-Za-z0-9\\-\\_]+)""", "-"),
                                    trendChartType: 'TOOLS_ONLY',
                                    qualityGates: [[threshold: 1, type: 'TOTAL', unstable: false]]
                                );
                            }
                        }
                    }
                    time_stage_started = new Date();
                }
            }
            currentBuild.result = allStagesPassed ? "SUCCESS" : "FAILED";
        }
    } finally {
        test_gerrit_helper.desc_add_line("Executed on: ${NODE_NAME} in ${WORKSPACE}");
        stage("Analyse Issues") {
            dir("${checkout_dir}") {
                xunit([
                    Custom(
                        customXSL: "$JENKINS_HOME/userContent/xunit/JUnit/0.1/pytest-xunit.xsl",
                        deleteOutputFiles: false,
                        failIfNotNew: true,
                        pattern: "results/*junit.xml",
                        skipNoTestFiles: true,
                        stopProcessingIfError: true,
                )]);

                show_duration("archiveArtifacts") {
                    archiveArtifacts(allowEmptyArchive: true, artifacts: 'results/**');
                }
            }
        }
    }
}

def main() {
    if ("${env.PARALLEL_CV_240_FEATURE_FLAG}" == "1") {
        main_parallel();
    } else {
        main_sequential();
    }
}

def update_result_table(static_description, table_data) {
    currentBuild.description = "<br><h3>${GERRIT_CHANGE_SUBJECT}</h3>" + render_description(table_data) + "<br>" + static_description;
}

def render_description(job_results) {
    def job_result_table_html = """<table><tr style='text-align: left; padding: 50px 50px;'>
    <th>${['Stage', 'Duration', 'Status', 'Issues', 'Test report', 'Report files'].join("</th><th>")}</th></tr>""";
    job_results.each { entry ->
        job_result_table_html += job_result_row(entry.value);
    };
    job_result_table_html += "</table>";
    return job_result_table_html;
}

def job_result_row(Map args) {
    // 'Stage'                    'Duration'      'Status'  'Parsed results'                'Result files'
    // Python Typing(<-JOB_URL)   11.078 seconds  success   (Analyser URL (<-ANALYSER_URL))  results/python-typing.txt(<-ARTIFACTS_URL)
    def pattern_url = "n/a";
    def triggered_build = args.stepName;
    def issue_link = "n/a";
    def test_result_link = "n/a";

    if (args.pattern != null && args.pattern != '--') {
        pattern_url = "<a href='artifact/${args.pattern}'>${args.pattern}</a>";
    }
    if (args.triggered_build_url) {
        triggered_build = "<a href='${args.triggered_build_url}'>${args.stepName}</a>";
    }
    if (args.unique_parser_name) {
        issue_link = "<a href='${currentBuild.absoluteUrl}/${args.unique_parser_name}'>issues</a>";
    }
    if (args.test_result_path && args.triggered_build_url) {
        test_result_link = "<a href='${currentBuild.absoluteUrl}/${args.test_result_path}'>test report</a>";
    }

    def totalSeconds = args.duration.days * 86400 + args.duration.hours * 3600 + args.duration.minutes * 60 + args.duration.seconds;
    def logSec = ((totalSeconds > 0) ? Math.log(totalSeconds) : 0 / Math.log(3)).toInteger();
    def dur_str = "${totalSeconds.intdiv(60)}m:${totalSeconds % 60}s ${"•" * Math.min(10, logSec)}${" " * (10 - Math.min(10, logSec))}";
    return """<tr>
    <td>${triggered_build}</td>
    <td style='font-family: monospace; white-space: pre; text-align: right;'>${dur_str}</td>
    <td style='color: ${['ongoing': 'blue', 'success': 'green', 'skipped': 'grey', 'failure': 'red'][args.status]};font-weight: bold;'>${args.status}</td>
    <td>${issue_link}</td>
    <td>${test_result_link}</td>
    <td>${pattern_url}</td>
    </tr>""";
}

return this;
