#!groovy

/// file: test-gerrit-single.groovy

// groovylint-disable MethodSize
void main() {
    check_job_parameters([
        "CIPARAM_NAME",
        "CIPARAM_DIR",
        "CIPARAM_ENV_VARS",
        "CIPARAM_ENV_VAR_LIST_STR",
        "CIPARAM_SEC_VAR_LIST_STR",
        "CIPARAM_GIT_FETCH_TAGS",
        "CIPARAM_GIT_FETCH_NOTES",
        "CIPARAM_COMMAND",
        "CIPARAM_RESULT_CHECK_FILE_PATTERN",
        // common-parameters
        "CUSTOM_GIT_REF",
        "CIPARAM_OVERRIDE_BUILD_NODE",
        "CIPARAM_CLEANUP_WORKSPACE",
    ]);

    def versioning = load("${checkout_dir}/buildscripts/scripts/utils/versioning.groovy");
    def artifacts_helper = load("${checkout_dir}/buildscripts/scripts/utils/upload_artifacts.groovy");

    def safe_branch_name = versioning.safe_branch_name();

    def env_var_list = [];
    def sec_var_list = [];
    def credentials = [];

    if (params.CIPARAM_ENV_VAR_LIST_STR) {
        env_var_list = params.CIPARAM_ENV_VAR_LIST_STR.split("#").collect {
            "${it}".replace("JOB_SPECIFIC_SPACE_PLACEHOLDER", "${checkout_dir}")
        };
    }
    if (params.CIPARAM_SEC_VAR_LIST_STR) {
        sec_var_list = params.CIPARAM_SEC_VAR_LIST_STR.split("#");
        credentials = sec_var_list.collect { string(credentialsId: it, variable: it)}
    }
    def result_dir = "${params.CIPARAM_RESULT_CHECK_FILE_PATTERN.split('/')[0]}";
    def extended_cmd = "set -x; ${params.CIPARAM_COMMAND}".replace(
        "JOB_SPECIFIC_SPACE_PLACEHOLDER", "${checkout_dir}"
    );
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
        |CIPARAM_COMMAND....................|${params.CIPARAM_COMMAND}|
        |extended_cmd.......................|${extended_cmd}|
        |CIPARAM_RESULT_CHECK_FILE_PATTERN..|${params.CIPARAM_RESULT_CHECK_FILE_PATTERN}|
        |result_dir.........................|${result_dir}|
        |===================================================
        """.stripMargin());

    smart_stage(
        name: "Fetch git notes/werk_mail{_fixes}",
        condition: params.CIPARAM_GIT_FETCH_NOTES,
    ) {
        dir("${checkout_dir}") {
            withCredentials([
                sshUserPrivateKey(
                    credentialsId: "jenkins-gerrit-fips-compliant-ssh-key",
                    keyFileVariable: 'KEYFILE'
                )
            ]) {
                withEnv(["GIT_SSH_COMMAND=ssh -o 'StrictHostKeyChecking no' -i ${KEYFILE} -l jenkins"]) {
                    // Since checkmk_ci:df2be57e we don't have the notes available anymore in the checkout
                    // however the werk commands tests heavily rely on them, so fetch them here.
                    // The order of the operations is important, because we rely on FETCH_HEAD
                    // being the checked out revision.
                    // Fetching with --shallow-since requires an explicit git commit hash to
                    // work properly.
                    // We use the same commit limitation as the werk commands uses in stages.yml.
                    sh("""
                        git fetch \
                            --no-tags \
                            --shallow-since=\$(date --date='4 weeks ago' --iso=seconds) \
                            origin \
                            \$(cat .git/FETCH_HEAD | cut -f 1)
                        git fetch origin 'refs/notes/werk_mail:refs/notes/werk_mail'
                        git fetch origin 'refs/notes/werk_mail_fixup:refs/notes/werk_mail_fixup'
                    """);
                }
            }
        }
    }

    smart_stage(
        name: "Fetch git tags",
        condition: params.CIPARAM_GIT_FETCH_TAGS,
    ) {
        dir("${checkout_dir}") {
            withCredentials([
                // groovylint-disable DuplicateMapLiteral
                sshUserPrivateKey(
                    credentialsId: "jenkins-gerrit-fips-compliant-ssh-key",
                    keyFileVariable: 'KEYFILE'
                )
            ]) {
                withEnv(["GIT_SSH_COMMAND=ssh -o 'StrictHostKeyChecking no' -i ${KEYFILE} -l jenkins"]) {
                    // Since checkmk_ci:df2be57e we don't have the tags available anymore in the checkout
                    // however the werk tests heavily rely on them, so fetch them here
                    sh("git fetch --depth=1 origin 'refs/tags/*:refs/tags/*'");
                }
            }
        }
    }

    stage("Prepare workspace") {
        dir("${checkout_dir}") {
            sh("""
                rm -rf ${result_dir}
                mkdir -p ${result_dir}
            """);
        }
    }

    stage("${params.CIPARAM_NAME} k8s") {
        dir("${checkout_dir}") {
            // The branch-specific part must not contain dots (e.g. 2.5.0),
            // because this results in an invalid branch name.
            // The pod templates uses - instead.
            def container_safe_branch_name = safe_branch_name.replace(".", "-");
            def container_name = "ubuntu-2404-${container_safe_branch_name}-latest";
            println("'execute_test' is using k8s container '${container_name}'");
            container(container_name) {
                withCredentials(credentials) {
                    withEnv(env_var_list) {
                        catchError(buildResult: 'FAILURE', stageResult: 'FAILURE') {
                            if (params.CIPARAM_DIR) {
                                extended_cmd = "cd ${params.CIPARAM_DIR}; ${extended_cmd}";
                            }
                            artifacts_helper.withHotCache([
                                download_dest: "~",
                                remove_existing_cache: true,
                                target_name: params.CIPARAM_NAME,
                                cache_prefix: versioning.distro_code(),
                                // When we mount the shared repository cache, we won't pack the repository cache under ~/.cache
                                // into the hot cache and therefore we dont need to consider WORKSPACE and MODULE.bazel.lock
                                files_to_consider: [
                                    '.bazelversion',
                                    'go.sum',
                                    'requirements.txt',
                                    'bazel/tools/package.json',
                                ] + (env.MOUNT_SHARED_REPOSITORY_CACHE == "1" ? [] : ['WORKSPACE', 'MODULE.bazel.lock']),
                                disable_hot_cache: env.USE_STASHED_BAZEL_FOLDER == "0",
                            ]) {
                                cmd_status = sh(script: "${extended_cmd}", returnStatus: true);
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
