#!groovy

/// file: build-cmk-distro-package.groovy

/// Builds a distribution package (.rpm, .dep, etc.) for a given edition/distribution
/// at a given git hash

/* groovylint-disable MethodSize */
def main() {
    check_job_parameters([
        ["EDITION", true],
        ["DISTRO", true],
        "VERSION",  // should be deprecated
        "DEPENDENCY_PATH_HASHES",
        "CIPARAM_OVERRIDE_DOCKER_TAG_BUILD",
        "DISABLE_CACHE",
    ]);

    check_environment_variables([
        "DOCKER_REGISTRY",
        "NEXUS_BUILD_CACHE_URL",
        "BAZEL_CACHE_URL",
    ]);

    def versioning = load("${checkout_dir}/buildscripts/scripts/utils/versioning.groovy");
    def bazel_logs = load("${checkout_dir}/buildscripts/scripts/utils/bazel_logs.groovy");

    def omd_env_vars = [
        "DEBFULLNAME='Checkmk Team'",
        "DEBEMAIL='feedback@checkmk.com'",
    ] + (params.DISABLE_CACHE ? [
        "NEXUS_BUILD_CACHE_URL=",
        "BAZEL_CACHE_URL=",
        "BAZEL_CACHE_USER=",
        "BAZEL_CACHE_PASSWORD="] : []);

    def distro = params.DISTRO;
    def edition = params.EDITION;

    def safe_branch_name = versioning.safe_branch_name(scm);
    def branch_version = versioning.get_branch_version(checkout_dir);

    // FIXME
    def cmk_version_rc_aware = versioning.get_cmk_version(safe_branch_name, branch_version, VERSION);

    def cmk_version = versioning.strip_rc_number_from_version(cmk_version_rc_aware);

    def docker_tag = versioning.select_docker_tag(
        CIPARAM_OVERRIDE_DOCKER_TAG_BUILD,  // 'build tag'
        safe_branch_name,                   // 'branch' returns '<BRANCH>-latest'
    );
    /* groovylint-disable LineLength */
    def container_name = "build-cmk-package-${distro}-${edition}-${cmd_output("git --git-dir=${checkout_dir}/.git log -n 1 --pretty=format:'%h'")}";
    /* groovylint-enable LineLength */

    def bazel_log_prefix = "bazel_log_";

    def causes = currentBuild.getBuildCauses();
    def triggerd_by = "";
    for(cause in causes) {
        triggerd_by += cause.upstreamProject + "/" + cause.upstreamBuild + "\n";
    }

    print(
        """
        |===== CONFIGURATION ===============================
        |distro:................... │${distro}│
        |edition:.................. │${edition}│
        |cmk_version:.............. │${cmk_version}│
        |safe_branch_name:......... │${safe_branch_name}│
        |omd_env_vars:............. │${omd_env_vars}│
        |docker_tag:............... │${docker_tag}│
        |checkout_dir:............. │${checkout_dir}│
        |container_name:........... │${container_name}│
        |triggerd_by:.............. |${triggerd_by}|
        |===================================================
        """.stripMargin());

    stage("Prepare workspace") {
        inside_container() {
            dir("${checkout_dir}") {
                sh("""
                    make buildclean
                    find . -name *.pth -delete
                """);
                versioning.configure_checkout_folder(edition, cmk_version);
            }

            // FIXME: should this be done by another job?
            dir("${checkout_dir}") {
                sh("make cmk-frontend frontend-vue");
            }

            dir("${checkout_dir}") {
                sh("make .venv");
            }

            stage("Fetch agent binaries") {

                upstream_build(
                    relative_job_name: "builders/build-linux-agent-updater",
                    build_params: [
                        DISABLE_CACHE: DISABLE_CACHE,
                        VERSION: VERSION,
                    ],
                    // TODO: SPoT!!, see https://jira.lan.tribe29.com/browse/CMK-13857
                    dependency_paths: ["agents", "non-free/cmk-update-agent"],
                    dest: "artifacts/build-linux-agent-updater",
                );
                dir("${checkout_dir}/artifacts/build-linux-agent-updater") {
                    sh("find .");
                    sh("""
                        cp *.deb *.rpm ${checkout_dir}/agents/
                        mkdir -p ${checkout_dir}/agents/linux
                        # artifact file flags are not being kept - building a tar would be better..
                        install -m 755 cmk-agent-ctl* mk-sql ${checkout_dir}/agents/linux/
                    """);
                    if (edition != "raw") {
                        sh("install -m 755 cmk-update-agent* ${checkout_dir}/non-free/cmk-update-agent/");
                    }
                }

                upstream_build(
                    relative_job_name: "winagt-build",  // TODO: move to builders
                    build_params: [
                        DISABLE_CACHE: DISABLE_CACHE,
                        VERSION: VERSION,
                    ],
                    // TODO: SPoT!!, see https://jira.lan.tribe29.com/browse/CMK-13857
                    dependency_paths: [
                        "agents/wnx",
                        "agents/windows",
                        "packages/cmk-agent-ctl",
                        "packages/mk-sql"
                    ],
                    dest: "artifacts/winagt-build",
                );
                dir("${checkout_dir}/artifacts/winagt-build") {
                    sh("find .");
                    // TODO: SPoT!!
                    sh("""
                       mkdir -p ${checkout_dir}/agents/windows
                       cp \
                        check_mk_agent-64.exe \
                        check_mk_agent.exe \
                        check_mk_agent.msi \
                        check_mk_agent_unsigned.msi \
                        check_mk.user.yml \
                        OpenHardwareMonitorLib.dll \
                        OpenHardwareMonitorCLI.exe \
                        mk-sql.exe \
                        robotmk_ext.exe \
                        windows_files_hashes.txt \
                        ${checkout_dir}/agents/windows/
                    """);
                }
                dir("${checkout_dir}/agents/windows") {
                    sh("""
                        ${checkout_dir}/buildscripts/scripts/create_unsign_msi_patch.sh \
                        check_mk_agent.msi check_mk_agent_unsigned.msi unsign-msi.patch
                    """);
                }

                upstream_build(
                    relative_job_name: "winagt-build-modules",  // TODO: move to builders
                    build_params: [
                        DISABLE_CACHE: DISABLE_CACHE,
                        VERSION: VERSION,
                    ],
                    // TODO: SPoT!!, see https://jira.lan.tribe29.com/browse/CMK-13857
                    dependency_paths: ["agents/modules/windows"],
                    dest: "artifacts/winagt-build-modules",
                );
                dir("${checkout_dir}/agents/windows") {
                    sh("find ${checkout_dir}/artifacts/winagt-build-modules");
                    sh("cp ${checkout_dir}/artifacts/winagt-build-modules/*.cab .");
                }
            }
        }
    }

    stage("Pull distro image") {
        shout("Pull distro image");
        docker.withRegistry(DOCKER_REGISTRY, 'nexus') {
            docker.image("${distro}:${docker_tag}").pull();
        }
    }

    stage("(lock resources)") {
        lock(label: "bzl_lock_${env.NODE_NAME.split('\\.')[0].split('-')[-1]}", quantity: 1, resource : null) {
            inside_container(
                image: docker.image("${distro}:${docker_tag}"),
                args: [
                    "--name ${container_name}",
                    " -v ${checkout_dir}:${checkout_dir}",
                    " --hostname ${distro}",
                ],
            ) {
                stage("Prepare environment") {
                    dir("${checkout_dir}") {
                        versioning.print_image_tag();
                        sh("make .venv");
                    }
                }
                stage("Build package") {
                    dir("${checkout_dir}") {
                        withCredentials([
                            usernamePassword(
                                credentialsId: 'nexus',
                                passwordVariable: 'NEXUS_PASSWORD',
                                usernameVariable: 'NEXUS_USERNAME'),
                            usernamePassword(
                                credentialsId: 'bazel-caching-credentials',
                                /// BAZEL_CACHE_URL must be set already, e.g. via Jenkins config
                                passwordVariable: 'BAZEL_CACHE_PASSWORD',
                                usernameVariable: 'BAZEL_CACHE_USER'),
                        ]) {
                            /// Don't use withEnv, see
                            /// https://issues.jenkins.io/browse/JENKINS-43632
                            sh("${omd_env_vars.join(' ')} make -C omd ${distro_package_type(distro)}");
                        }
                    }
                }
            }
        }
    }

    stage("Plot cache hits") {
        bazel_logs.try_parse_bazel_execution_log(distro, checkout_dir, bazel_log_prefix);
        bazel_logs.try_plot_cache_hits(bazel_log_prefix, [distro]);
    }

    stage("Archive stuff") {
        dir("${checkout_dir}") {
            setCustomBuildProperty(
                key: "path_hashes",
                value: scm_directory_hashes(scm.extensions)
            );
            show_duration("archiveArtifacts") {
                archiveArtifacts(
                    artifacts: "*.deb,*.rpm,*.cma",
                    fingerprint: true,
                );
            }
        }
    }
}

return this;
