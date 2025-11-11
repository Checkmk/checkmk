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
        "CIPARAM_OVERRIDE_DOCKER_TAG_BUILD",
        "DISABLE_CACHE",
        // TODO: Rename to FAKE_AGENT_ARTIFACTS -> we're also faking the linux updaters now
        "FAKE_WINDOWS_ARTIFACTS",
    ]);

    check_environment_variables([
        "DOCKER_REGISTRY",
        "NEXUS_BUILD_CACHE_URL",
        "BAZEL_CACHE_URL",
    ]);

    def versioning = load("${checkout_dir}/buildscripts/scripts/utils/versioning.groovy");
    def bazel_logs = load("${checkout_dir}/buildscripts/scripts/utils/bazel_logs.groovy");
    def package_helper = load("${checkout_dir}/buildscripts/scripts/utils/package_helper.groovy");

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
    def version = params.VERSION;
    def disable_cache = params.DISABLE_CACHE;

    def safe_branch_name = versioning.safe_branch_name();
    def branch_version = versioning.get_branch_version(checkout_dir);
    def branch_base_folder = package_helper.branch_base_folder(false);

    // FIXME
    def cmk_version_rc_aware = versioning.get_cmk_version(safe_branch_name, branch_version, VERSION);

    def cmk_version = versioning.strip_rc_number_from_version(cmk_version_rc_aware);

    def docker_tag = versioning.select_docker_tag(
        CIPARAM_OVERRIDE_DOCKER_TAG_BUILD,  // 'build tag'
        safe_branch_name,                   // 'branch' returns '<BRANCH>-latest'
    );

    def checkout_hash = checkout_commit_id.substring(0, 6);
    def workspace_hash = String.format("%06x", WORKSPACE.hashCode());
    def container_name = "build-cmk-package-${distro}-${edition}-${workspace_hash}-${checkout_hash}";

    def bazel_log_prefix = "bazel_log_";

    def package_type = distro_package_type(distro);
    def package_name = "";

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
        |container_name:........... │${checkout_dir}│
        |package_type:............. │${package_type}│
        |===================================================
        """.stripMargin());

    // this is a quick fix for FIPS based tests, see CMK-20851
    if (params.CIPARAM_OVERRIDE_BUILD_NODE == "fips") {
        // Builds can not be done on FIPS node
        error("Package builds can not be done on FIPS node");
    }

    stage("Prepare workspace") {
        inside_container() {
            dir("${checkout_dir}") {
                sh("make buildclean");

                sh("find . -name *.pth -delete");

                versioning.configure_checkout_folder(edition, cmk_version);
            }

            // FIXME: should this be done by another job?
            dir("${checkout_dir}") {
                sh("make .ran-webpack");
            }
        }
    }

    def stages = [
        "Build BOM": {
            def build_instance = null;
            smart_stage(
                name: "Build BOM",
                raiseOnError: true,
            ) {
                build_instance = smart_build(
                    // see global-defaults.yml, needs to run in minimal container
                    use_upstream_build: true,
                    relative_job_name: "${branch_base_folder}/builders/build-cmk-bom",
                    build_params: [
                        CUSTOM_GIT_REF: effective_git_ref,
                        VERSION: version,
                        EDITION: edition,
                        DISABLE_CACHE: disable_cache,
                    ],
                    build_params_no_check: [
                        CIPARAM_OVERRIDE_BUILD_NODE: params.CIPARAM_OVERRIDE_BUILD_NODE,
                        CIPARAM_CLEANUP_WORKSPACE: params.CIPARAM_CLEANUP_WORKSPACE,
                        CIPARAM_BISECT_COMMENT: params.CIPARAM_BISECT_COMMENT,
                    ],
                    no_remove_others: true, // do not delete other files in the dest dir
                    download: false,    // use copyArtifacts to avoid nested directories
                );
            }
            smart_stage(
                name: "Copy artifacts",
                condition: build_instance,
                raiseOnError: true,
            ) {
                copyArtifacts(
                    projectName: "${branch_base_folder}/builders/build-cmk-bom",
                    selector: specific(build_instance.getId()),
                    target: "${checkout_dir}",
                    fingerprintArtifacts: true,
                )
            }
        },
    ];

    if (!params.FAKE_WINDOWS_ARTIFACTS) {
        stages += package_helper.provide_agent_binaries(
            version: version,
            edition: edition,
            disable_cache: disable_cache,
            bisect_comment: params.CIPARAM_BISECT_COMMENT,
            artifacts_base_dir: "tmp_artifacts",
        );
    }
    else {
        smart_stage(name: 'Fake agent binaries', condition: params.FAKE_WINDOWS_ARTIFACTS) {
            dir("${checkout_dir}") {
                sh("scripts/fake-artifacts");
            }
        }
    }

    inside_container_minimal(safe_branch_name: safe_branch_name) {
        currentBuild.result = parallel(stages).values().every { it } ? "SUCCESS" : "FAILURE";
    }

    package_helper.cleanup_provided_agent_binaries("tmp_artifacts");

    stage("Pull distro image") {
        docker.withRegistry(DOCKER_REGISTRY, 'nexus') {
            docker.image("${distro}:${docker_tag}").pull();
        }
    }

    stage("Build package") {
        lock(label: 'bzl_lock_' + env.NODE_NAME.split("\\.")[0].split("-")[-1], quantity: 1, resource : null) {
            dir("${checkout_dir}") {
                inside_container(
                    image: docker.image("${distro}:${docker_tag}"),
                    args: [
                        "--name ${container_name}",
                        " --hostname ${distro}",
                    ],
                ) {
                    versioning.print_image_tag();

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
                        // Don't use withEnv, see
                        // https://issues.jenkins.io/browse/JENKINS-43632
                        sh("""
                            ${omd_env_vars.join(' ')} \
                            make -C omd ${package_type}
                        """);

                        package_name = cmd_output("ls check-mk-${edition}-${cmk_version}*.${package_type}");
                        if (!package_type) {
                            error("No package 'check-mk-${edition}-${cmk_version}*.${package_type}' found in ${checkout_dir}");
                        }

                        bazel_logs.try_parse_bazel_execution_log(distro, checkout_dir, bazel_log_prefix)
                    }
                }
            }
        }
    }

    inside_container(ulimit_nofile: 2048) {
        stage("Sign package") {
            package_helper.sign_package(
                checkout_dir,
                "${checkout_dir}/${package_name}"
            );
        }

        stage("Test package") {
            // quell ewiger freude: venv created by another container not usable by this container
            sh("rm -rf ${checkout_dir}/.venv");

            package_helper.test_package(
                "${checkout_dir}/${package_name}",
                distro,
                WORKSPACE,
                checkout_dir,
                cmk_version
            );
        }
    }

    stage("Plot cache hits") {
        bazel_logs.try_plot_cache_hits(bazel_log_prefix, [distro]);
    }

    stage("Archive stuff") {
        dir("${checkout_dir}") {
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
