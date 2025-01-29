#!groovy

/// file: build-linux-agent-updater.groovy


def main() {
    check_job_parameters([
        "DISABLE_CACHE",
        "VERSION",
    ]);

    check_environment_variables([
        "DOCKER_REGISTRY",
    ]);

    def versioning = load("${checkout_dir}/buildscripts/scripts/utils/versioning.groovy");
    def package_helper = load("${checkout_dir}/buildscripts/scripts/utils/package_helper.groovy");

    shout("configure");

    def branch_version = versioning.get_branch_version(checkout_dir);

    def safe_branch_name = versioning.safe_branch_name(scm);
    def cmk_version_rc_aware = versioning.get_cmk_version(safe_branch_name, branch_version, VERSION);
    def cmk_version = versioning.strip_rc_number_from_version(cmk_version_rc_aware);

    /// Get the ID of the docker group from the node(!). This must not be
    /// executed inside the container (as long as the IDs are different)
    def docker_group_id = get_docker_group_id();

    print(
        """
        |===== CONFIGURATION ===============================
        |branch_version:........... │${branch_version}│
        |cmk_version_rc_aware:..... │${cmk_version_rc_aware}│
        |cmk_version:.............. │${cmk_version}│
        |safe_branch_name:......... │${safe_branch_name}│
        |docker_group_id:.......... │${docker_group_id}│
        |docker_registry_no_http:.. │${docker_registry_no_http}│
        |checkout_dir:............. │${checkout_dir}│
        |===================================================
        """.stripMargin());

    inside_container(
        set_docker_group_id: true,
        priviliged: true,
    ) {
        // TODO: check why this doesn't work
        // docker_reference_image().inside(docker_args) {

        dir("${checkout_dir}") {
            sh("""
                make buildclean
                rm -rf ${WORKSPACE}/build
            """);
            versioning.set_version(cmk_version);
        }

        def agent_builds = ["au-linux-64bit", "au-linux-32bit"].collectEntries { agent ->
            [("agent ${agent}") : {
                stage("Build Agent for ${agent}") {
                    def suffix = agent == "au-linux-32bit" ? "-32" : "";
                    withCredentials([
                        usernamePassword(
                            credentialsId: 'nexus',
                            passwordVariable: 'NEXUS_PASSWORD',
                            usernameVariable: 'NEXUS_USERNAME')
                    ]) {
                        dir("${checkout_dir}/non-free/cmk-update-agent") {
                            sh("""
                                BRANCH_VERSION=${branch_version} \
                                DOCKER_REGISTRY_NO_HTTP=${docker_registry_no_http} \
                                ./make-agent-updater${suffix}
                            """);
                        }
                    }
                    dir("${WORKSPACE}/build") {
                        sh("cp ${checkout_dir}/non-free/cmk-update-agent/cmk-update-agent${suffix} .");
                    }
                }
            }]
        }
        parallel agent_builds;

        stage("Create and sign deb/rpm packages") {
            dir("${checkout_dir}/agents") {
                sh("make rpm");
                sh("make deb");
            }
            def package_name_rpm = cmd_output("find ${checkout_dir} -name *.rpm");
            def package_name_deb = cmd_output("find ${checkout_dir} -name *.deb");
            package_helper.sign_package(checkout_dir, package_name_rpm)
            dir("${WORKSPACE}/build") {
                sh("""
                    cp ${package_name_rpm} .
                    cp ${package_name_deb} .
                    cp ${checkout_dir}/agents/linux/cmk-agent-ctl* .
                    cp ${checkout_dir}/agents/linux/mk-sql* .
                """);
            }
        }
    }

    stage("Archive artifacts") {
        dir("${checkout_dir}") {
            setCustomBuildProperty(
                key: "path_hashes",
                // TODO: this must go to some SPoT
                value: directory_hashes(["agents", "non-free/cmk-update-agent"])
            );
        }
        dir("${WORKSPACE}/build") {
            show_duration("archiveArtifacts") {
                archiveArtifacts(
                    artifacts: "**/*",
                    fingerprint: true,
                );
            }
        }
    }
}

return this;
