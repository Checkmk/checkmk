#!groovy

/// file: build-cmk-distro-package.groovy

/// Builds a distribution package (.rpm, .dep, etc.) for a given edition/distribution
/// at a given git hash

def main() {
    check_job_parameters([
        ["EDITION", true],
        ["DISTRO", true],
        "VERSION",  // should be deprecated
        "DEPENDENCY_PATH_HASHES",
        "DOCKER_TAG_BUILD",
        "DISABLE_CACHE",
    ]);

    check_environment_variables([
        "DOCKER_REGISTRY",
        "NEXUS_BUILD_CACHE_URL",
        "BAZEL_CACHE_URL",
    ]);

    def versioning = load("${checkout_dir}/buildscripts/scripts/utils/versioning.groovy");
    def artifacts_helper = load("${checkout_dir}/buildscripts/scripts/utils/upload_artifacts.groovy");

    def docker_args = "${mount_reference_repo_dir}";
    def omd_env_vars = [
        "DEBFULLNAME='Checkmk Team'",
        "DEBEMAIL='feedback@checkmk.com'",
    ] + (params.DISABLE_CACHE ? [
        "NEXUS_BUILD_CACHE_URL=",
        "PYTHON_ENABLE_OPTIMIZATIONS=",
        "BAZEL_CACHE_URL=",
        "BAZEL_CACHE_USER=",
        "BAZEL_CACHE_PASSWORD="] : []);

    def distro = params.DISTRO;
    def edition = params.EDITION;

    // FIXME
    // def branch_name = versioning.safe_branch_name(scm);
    def branch_name = "master";
    def branch_version = versioning.get_branch_version(checkout_dir);

    //FIXME
    def cmk_version_rc_aware = versioning.get_cmk_version(branch_name, branch_version, VERSION);

    def cmk_version = versioning.strip_rc_number_from_version(cmk_version_rc_aware);

    def docker_tag = versioning.select_docker_tag(branch_name, DOCKER_TAG_BUILD, DOCKER_TAG_BUILD);
    def container_name = "build-cmk-package-${distro}-${edition}-${cmd_output("git --git-dir=${checkout_dir}/.git log -n 1 --pretty=format:'%h'")}";

    print(
        """
        |===== CONFIGURATION ===============================
        |distro:................... │${distro}│
        |edition:.................. │${edition}│
        |cmk_version:.............. │${cmk_version}│
        |branch_name:.............. │${branch_name}│
        |omd_env_vars:............. │${omd_env_vars}│
        |docker_tag:............... │${docker_tag}│
        |docker_args:.............. │${docker_args}│
        |checkout_dir:............. │${checkout_dir}│
        |container_name:........... │${checkout_dir}│
        |===================================================
        """.stripMargin());

    stage("Prepare workspace") {
        docker.withRegistry(DOCKER_REGISTRY, 'nexus') {
            docker_image_from_alias("IMAGE_TESTING").inside("${docker_args}") {

                dir("${checkout_dir}") {
                    sh("make buildclean");

                    sh("find . -name *.pth -delete");

                    versioning.configure_checkout_folder(edition, cmk_version);
                }

                // FIXME: should this be done by another job?
                dir("${checkout_dir}") {
                    sh("make .ran-webpack");
                }

                stage("Fetch agent binaries") {
                    // shout("Fetch agent binaries");

                    fetch_job_artifacts(
                        relative_job_name: "builders/build-linux-agent-updater",
                        params: [
                            DISABLE_CACHE: DISABLE_CACHE,
                            VERSION: VERSION,
                        ],
                        // TODO: SPoT!!, see https://jira.lan.tribe29.com/browse/CMK-13857
                        dependency_paths: ["agents", "non-free/cmk-update-agent"],
                        dest: "artifacts/build-linux-agent-updater",
                    );
                    dir("${checkout_dir}/artifacts/build-linux-agent-updater") {
                        sh("find .");
                        sh("cp *.deb *.rpm ${checkout_dir}/agents/");
                        sh("mkdir -p ${checkout_dir}/agents/linux");
                        sh("cp cmk-agent-ctl* check-sql ${checkout_dir}/agents/linux/");
                        if (edition != "raw") {
                            sh("cp cmk-update-agent* ${checkout_dir}/non-free/cmk-update-agent/");
                        }
                    }

                    fetch_job_artifacts(
                        relative_job_name: "winagt-build",  // TODO: move to builders
                        params: [
                            DISABLE_CACHE: DISABLE_CACHE,
                            VERSION: VERSION,
                        ],
                        // TODO: SPoT!!, see https://jira.lan.tribe29.com/browse/CMK-13857
                        dependency_paths: [
                            "agents/wnx",
                            "agents/windows",
                            "packages/cmk-agent-ctl",
                            "packages/check-sql"
                        ],
                        dest: "artifacts/winagt-build",
                    );
                    dir("${checkout_dir}/artifacts/winagt-build") {
                        sh("find .");
                        sh("mkdir -p ${checkout_dir}/agents/windows");
                        // TODO: SPoT!!
                        sh("""cp \
                            check_mk_agent-64.exe \
                            check_mk_agent.exe \
                            check_mk_agent.msi \
                            check_mk_agent_unsigned.msi \
                            check_mk.user.yml \
                            OpenHardwareMonitorLib.dll \
                            OpenHardwareMonitorCLI.exe \
                            check-sql.exe \
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

                    fetch_job_artifacts(
                        relative_job_name: "winagt-build-modules",  // TODO: move to builders
                        params: [
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
    }

    stage("Pull distro image") {
        shout("Pull distro image");
        docker.withRegistry(DOCKER_REGISTRY, 'nexus') {
            docker.image("${distro}:${docker_tag}").pull();
        }
    }

    stage("Prepare environment") {
        shout("Prepare environment");
        lock(label: 'bzl_lock_' + env.NODE_NAME.split("\\.")[0].split("-")[-1], quantity: 1, resource : null) {
        docker.withRegistry(DOCKER_REGISTRY, 'nexus') {
            docker.image("${distro}:${docker_tag}").inside(
                    "--name ${container_name}" +
                    " ${docker_args} " +
                    "-v ${checkout_dir}:${checkout_dir} " +
                    "--hostname ${distro}") {
                sh("""
                    cd ${checkout_dir}
                    make .venv
                """);
                withCredentials([
                    usernamePassword(
                        credentialsId: 'nexus',
                        passwordVariable: 'NEXUS_PASSWORD',
                        usernameVariable: 'NEXUS_USERNAME'),
                    usernamePassword(
                        credentialsId: 'bazel-caching-credentials',
                        /// BAZEL_CACHE_URL must be set already, e.g. via Jenkins config
                        passwordVariable: 'BAZEL_CACHE_PASSWORD',
                        usernameVariable: 'BAZEL_CACHE_USER')
                ]) {
                    versioning.print_image_tag();
                    // Don't use withEnv, see
                    // https://issues.jenkins.io/browse/JENKINS-43632
                    stage("Build package") {
                        sh("""
                            cd ${checkout_dir}/omd

                            # ps wauxw | grep bazel
                            # bazel clean
                            #strace \
                            #    --trace='fork,vfork,clone,clone3,execve,openat,write' \
                            #    -ttt \
                            #    -f --decode-pids='pidns' \
                            #    --columns=0 --abbrev='none' -s 65536 \
                            #    -o "make-omd.strace.log" \
                            ps wauxw | grep bazel

                            ${omd_env_vars.join(' ')} \
                            make ${distro_package_type(distro)}
                        """);
                    }
                }
            }
        }
        }
    }

    stage("Archive stuff") {
        dir("${checkout_dir}") {
            setCustomBuildProperty(
                key: "path_hashes",
                value: scm_directory_hashes(scm.extensions));
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
