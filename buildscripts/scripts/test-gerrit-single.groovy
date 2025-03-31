#!groovy

/// file: test-gerrit-single.groovy

def main() {
    check_job_parameters([
        "CIPARAM_NAME",
        "CIPARAM_DIR",
        "CIPARAM_ENV_VARS",
        "CIPARAM_ENV_VAR_LIST_STR",
        "CIPARAM_SEC_VAR_LIST_STR",
        "CIPARAM_JENKINS_API_ACCESS",
        "CIPARAM_COMMAND",
        "CIPARAM_RESULT_CHECK_FILE_PATTERN",
        "CIPARAM_BAZEL_LOCKS_AMOUNT",
        // common-parameters
        "CUSTOM_GIT_REF",
        "CIPARAM_OVERRIDE_BUILD_NODE",
        "CIPARAM_CLEANUP_WORKSPACE",
    ]);

    test_jenkins_helper = load("${checkout_dir}/buildscripts/scripts/utils/test_helper.groovy");

    def env_var_list = [];
    def sec_var_list = [];
    def credentials = [];
    def bazel_locks_amount = params.BAZEL_LOCKS_AMOUNT ? params.BAZEL_LOCKS_AMOUNT.toInteger() : -1;

    if (params.CIPARAM_ENV_VAR_LIST_STR) {
        env_var_list = params.CIPARAM_ENV_VAR_LIST_STR.split("#").collect { "${it}".replace("JOB_SPECIFIC_SPACE_PLACEHOLDER", "${checkout_dir}") };
    }
    if (params.CIPARAM_SEC_VAR_LIST_STR) {
        sec_var_list = params.CIPARAM_SEC_VAR_LIST_STR.split("#");
        credentials = sec_var_list.collect{string(credentialsId: it, variable: it)}
    }
    if (params.JENKINS_API_ACCESS) {
        credentials.add(usernamePassword(
            credentialsId: 'jenkins-api-token',
            usernameVariable: 'JENKINS_USERNAME',
            passwordVariable: 'JENKINS_PASSWORD'
        ))
    }
    def result_dir = "${params.CIPARAM_RESULT_CHECK_FILE_PATTERN.split('/')[0]}";
    def extended_cmd = "set -x; ${params.CIPARAM_COMMAND}".replace("JOB_SPECIFIC_SPACE_PLACEHOLDER", "${checkout_dir}");
    def cmd_status = 1; // be sure to fail, in case of other failures

    print(
        """
        |===== CONFIGURATION ===============================
        |CIPARAM_NAME.......................|${params.CIPARAM_NAME}|
        |CIPARAM_DIR........................|${params.CIPARAM_DIR}|
        |CIPARAM_ENV_VARS...................|${params.CIPARAM_ENV_VARS}|
        |ENV_VAR_LIST.......................|${params.CIPARAM_ENV_VAR_LIST_STR}|
        |env_var_list.......................|${env_var_list}|
        |SEC_VAR_LIST.......................|${params.CIPARAM_SEC_VAR_LIST_STR}|
        |sec_var_list.......................|${sec_var_list}|
        |JENKINS_API_ACCESS.................|${params.JENKINS_API_ACCESS}|
        |CIPARAM_COMMAND....................|${params.CIPARAM_COMMAND}|
        |extended_cmd.......................|${extended_cmd}|
        |CIPARAM_RESULT_CHECK_FILE_PATTERN..|${params.CIPARAM_RESULT_CHECK_FILE_PATTERN}|
        |result_dir.........................|${result_dir}|
        |===================================================
        """.stripMargin());

    stage("Prepare workspace") {
        dir("${checkout_dir}") {
            inside_container() {
                sh("buildscripts/scripts/ensure-workspace-integrity");
            }
            sh("""
                rm -rf ${result_dir}
                mkdir -p ${result_dir}
            """);
        }
    }

    stage(params.CIPARAM_NAME) {
        dir("${checkout_dir}") {
            sh(script: "figlet -w 150 '${params.CIPARAM_NAME}'", returnStatus: true);
            println("Execute: ${extended_cmd} in ${params.CIPARAM_DIR}");

            inside_container(privileged: true, set_docker_group_id: true) {
                withCredentials(credentials) {
                    withEnv(env_var_list) {
                        catchError(buildResult: 'FAILURE', stageResult: 'FAILURE') {
                            dir(params.CIPARAM_DIR) {
                                // be very carefull here. Setting quantity to 0 or null, takes all available resources
                                if (bazel_locks_amount >= 1) {
                                    lock(
                                        label: 'bzl_lock_' + env.NODE_NAME.split("\\.")[0].split("-")[-1],
                                        quantity: bazel_locks_amount,
                                        resource : null
                                    ) {
                                        cmd_status = sh(script: "${extended_cmd}", returnStatus: true);
                                    }
                                } else {
                                    cmd_status = sh(script: "${extended_cmd}", returnStatus: true);
                                }
                            }

                            archiveArtifacts(
                                artifacts: "${result_dir}/**",
                                fingerprint: true,
                            );

                            /// make the stage fail if the command returned nonzero
                            sh("exit ${cmd_status}");
                        }
                    }
                }
            }
        }
    }
}

return this;
