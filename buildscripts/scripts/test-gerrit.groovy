#!groovy

/// file: test-gerrit.groovy

def main() {
    def test_gerrit_helper = load("${checkout_dir}/buildscripts/scripts/utils/gerrit_stages.groovy");
    // no `def` - must be global
    test_jenkins_helper = load("${checkout_dir}/buildscripts/scripts/utils/test_helper.groovy");
    def versioning = load("${checkout_dir}/buildscripts/scripts/utils/versioning.groovy");

    def result_dir = "${checkout_dir}/results";
    def time_job_started = new Date();
    def time_stage_started = time_job_started;
    def safe_branch_name = versioning.safe_branch_name(scm);

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

    time_stage_started = test_gerrit_helper.log_stage_duration(time_stage_started);

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
        time_stage_started = test_gerrit_helper.log_stage_duration(time_stage_started);
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
                time_stage_started = test_gerrit_helper.log_stage_duration(time_stage_started);
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
                    time_stage_started = test_gerrit_helper.log_stage_duration(time_stage_started);
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
        time_stage_started = test_gerrit_helper.log_stage_duration(time_stage_started);
    }
}

return this;
