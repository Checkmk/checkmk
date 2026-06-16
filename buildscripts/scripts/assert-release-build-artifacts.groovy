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

    print(
        """
        |===== CONFIGURATION ===============================
        |safe_branch_name:......... │${safe_branch_name}│
        |cmk_version:.............. │${cmk_version}│
        |cmk_version_rc_aware:..... │${cmk_version_rc_aware}│
        |branch_version:........... │${branch_version}│
        |===================================================
        """.stripMargin());

    stage("Assert release build artifacts") {
        inside_container(
            set_docker_group_id: true,
            mount_credentials: true,
            privileged: true,
        ) {
            withCredentials([
                usernamePassword(
                    credentialsId: 'nexus',
                    passwordVariable: 'NEXUS_PASSWORD',
                    usernameVariable: 'NEXUS_USER')]) {
                withEnv(["PYTHONUNBUFFERED=1"]) {
                    dir("${checkout_dir}") {
                        def result = sh(
                            script: """scripts/run-uvenv \
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
                                from: "\"CI\" <${JENKINS_MAIL}>",
                                replyTo: "${TEAM_CI_MAIL}",
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
}

return this;
