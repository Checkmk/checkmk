#!groovy

// file: assert-release-build-artifacts.groovy

// groovylint-disable MethodSize
void main() {
    check_job_parameters([
        "VERSION",
        "USE_CASE",
    ])

    def versioning = load("${checkout_dir}/buildscripts/scripts/utils/versioning.groovy");

    def safe_branch_name = versioning.safe_branch_name();
    def branch_version = versioning.get_branch_version(checkout_dir);
    def cmk_version_rc_aware = versioning.get_cmk_version(safe_branch_name, branch_version, params.VERSION).replaceAll("\\+security", "");
    def cmk_version = versioning.strip_rc_number_from_version(cmk_version_rc_aware);

    def use_case = params.USE_CASE.trim() ?: "daily";

    def all_editions = [];

    inside_container_minimal(safe_branch_name: safe_branch_name) {
        // run everything requiring python in this container
        all_editions = versioning.get_editions();
    }

    print(
        """
        |===== CONFIGURATION ===============================
        |branch_version:........... │${branch_version}│
        |cmk_version:.............. │${cmk_version}│
        |cmk_version_rc_aware:..... │${cmk_version_rc_aware}│
        |safe_branch_name:......... │${safe_branch_name}│
        |===================================================
        """.stripMargin());

    dir("${checkout_dir}") {
        stage("Assert release build artifacts") {
            inside_container_minimal(safe_branch_name: safe_branch_name) {
                withCredentials([
                    usernamePassword(
                        credentialsId: 'nexus',
                        passwordVariable: 'NEXUS_PASSWORD',
                        usernameVariable: 'NEXUS_USER')
                ]) {
                    withCredentialUsernamePasswordAtLocation(
                        creds: [
                            [credentialsId: "cmk-credentials", location: "/etc/.cmk-credentials"]
                        ]
                    ) {
                        withEnv(["PYTHONUNBUFFERED=1"]) {
                            def result = sh(
                                script: """python3 \
                                buildscripts/scripts/assert_build_artifacts.py \
                                --editions_file "${checkout_dir}/editions.yml" \
                                assert_build_artifacts \
                                --version "${cmk_version_rc_aware}" \
                                --use_case "${use_case}"
                                """,
                                returnStatus: true,
                            );

                            /// Team Donau wants to be explicitly notified about the missing relay image.
                            /// returnCode == 2 means at least the relay is missing on dockerhub.
                            if (result == 2 && use_case == "release") {
                                mail(
                                    to: "team-donau@checkmk.com",
                                    from: "\"CI\" <${env.JENKINS_MAIL}>",
                                    replyTo: "${env.TEAM_CI_MAIL}",
                                    subject: "[Release] Relay image missing on Docker Hub: checkmk/check-mk-relay:${cmk_version}",
                                    body: ("""
        |The relay image checkmk/check-mk-relay:${cmk_version} is not available on Docker Hub.
        |
        |Please get in touch with the release coordinator (see slack channel #release-coordination).
        |
        |Build: ${env.BUILD_URL}
        |""".stripMargin()),
                                );
                            }

                            if (result != 0) {
                                error("assert_build_artifacts failed");
                            }
                        }
                    }
                }
            }
        }

        stage("Assert Docker images") {
            def docker_file_location = "dirty_workspace/Dockerfile";
            def docker_build_args = (""
                + " --dockerfile=${docker_file_location}"
                + " --context ${docker_file_location.split('/')[0]}"
                + " --destination unused:latest"
                + " --no-push"
            );
            def docker_result = 1;
            def container_name_base = "";
            withCredentials([
                usernamePassword(
                    credentialsId: 'nexus',
                    passwordVariable: 'NEXUS_PASSWORD',
                    usernameVariable: 'NEXUS_USERNAME')
            ]) {
                for (edition in all_editions) {
                    println("docker_build_args: ${docker_build_args}");
                    container("kaniko-alpine") {
                        if (edition == "cloud") {
                            container_name_base = "artifacts.lan.tribe29.com:4000";
                            /* groovylint-disable LineLength */
                            sh("""#!/bin/sh
                                echo '{"auths":{"${docker_registry_no_http}":{"username":"${NEXUS_USERNAME}","password":"${NEXUS_PASSWORD}"}}}' > /kaniko/.docker/config.json
                            """);
                            /* groovylint-enable LineLength */
                        } else {
                            container_name_base = "checkmk";
                            sh("""#!/bin/sh
                                rm /kaniko/.docker/config.json || true
                            """);
                        }

                        sh("""#!/bin/sh
                            mkdir -p dirty_workspace
                            echo "FROM ${container_name_base}/check-mk-${edition}:${cmk_version_rc_aware}" > ${docker_file_location}
                            echo "RUN echo 'Hello'" >> ${docker_file_location}
                        """);

                        docker_result = sh(
                            script: """#!/bin/sh
                                /kaniko/executor ${docker_build_args}
                            """,
                            returnStatus: true,
                        );
                    }
                    if (docker_result != 0) {
                        error("Failed to verify Docker image availability");
                    }
                }
            }
        }
    }
}

return this;
