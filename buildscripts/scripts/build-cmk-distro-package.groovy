#!groovy

/// file: build-cmk-distro-package.groovy

/// Builds a distribution package (.rpm, .dep, etc.) for a given edition/distribution
/// at a given git hash

def main() {
    check_job_parameters([
        ["EDITION", true],
        ["DISTRO", true],
        ["VERSION", true],
        "DEPENDENCY_PATH_HASHES",
        "CIPARAM_OVERRIDE_DOCKER_TAG_BUILD",
        "DISABLE_CACHE",
        // TODO: Rename to FAKE_AGENT_ARTIFACTS -> we're also faking the linux updaters now
        "FAKE_WINDOWS_ARTIFACTS",
    ]);

    check_environment_variables([
        "DOCKER_REGISTRY",
        "NEXUS_BUILD_CACHE_URL",
    ]);

    def distro = params.DISTRO;
    def edition = params.EDITION;
    def version = params.VERSION;
    def disable_cache = params.DISABLE_CACHE;

    def versioning = load("${checkout_dir}/buildscripts/scripts/utils/versioning.groovy");
    def bazel_logs = load("${checkout_dir}/buildscripts/scripts/utils/bazel_logs.groovy");
    def package_helper = load("${checkout_dir}/buildscripts/scripts/utils/package_helper.groovy");

    def omd_env_vars = [
        "DEBFULLNAME='Checkmk Team'",
        "DEBEMAIL='feedback@checkmk.com'",
    ] + (disable_cache ? [
        "NEXUS_BUILD_CACHE_URL=",
        ] : []);

    def safe_branch_name = versioning.safe_branch_name();
    def branch_version = versioning.get_branch_version(checkout_dir);
    def branch_base_folder = package_helper.branch_base_folder(with_testing_prefix: false);

    // FIXME
    def cmk_version_rc_aware = versioning.get_cmk_version(safe_branch_name, branch_version, version);

    def cmk_version = versioning.strip_rc_number_from_version(cmk_version_rc_aware);

    def docker_tag = versioning.select_docker_tag(
        CIPARAM_OVERRIDE_DOCKER_TAG_BUILD,  // 'build tag'
        safe_branch_name,                   // 'branch' returns '<BRANCH>-latest'
    );

    def checkout_hash = checkout_commit_id.substring(0, 6);
    def workspace_hash = String.format("%06x", WORKSPACE.hashCode());
    def container_name = "build-cmk-package-${distro}-${edition}-${workspace_hash}-${checkout_hash}";

    def bazel_log_prefix = "bazel_log_";

    def causes = currentBuild.getBuildCauses();
    def triggerd_by = "";
    for(cause in causes) {
        if (cause.upstreamProject != null) {
            triggerd_by += cause.upstreamProject + "/" + cause.upstreamBuild + "\n";
        }
    }
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
        |container_name:........... │${container_name}│
        |triggerd_by:.............. │${triggerd_by}│
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
                sh("""
                    make buildclean
                    find . -name *.pth -delete
                """);
                versioning.configure_checkout_folder(edition, cmk_version);
            }

            // FIXME: should this be done by another job?
            dir("${checkout_dir}") {
                sh("make cmk-frontend-build frontend-vue-build");
            }
        }

        inside_container_minimal(safe_branch_name: safe_branch_name) {
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

            smart_stage(
                name: 'Fetch agent binaries',
                condition: !params.FAKE_WINDOWS_ARTIFACTS,
                raiseOnError: true,
            ) {
                package_helper.provide_agent_binaries(version, edition, disable_cache, params.CIPARAM_BISECT_COMMENT);
            }

            smart_stage(name: 'Fake agent binaries', condition: params.FAKE_WINDOWS_ARTIFACTS) {
                dir("${checkout_dir}") {
                    sh("scripts/fake-artifacts");
                }
            }
        }
    }

    stage("Build package") {
        lock(label: "bzl_lock_${env.NODE_NAME.split('\\.')[0].split('-')[-1]}", quantity: 1, resource : null) {
            dir("${checkout_dir}") {
                // supplying the registry explicitly might not be needed but it looks like
                // image.inside() will first try to use the image without registry and only
                // if that didn't work falls back to the fully qualified name
                inside_container(
                    image: docker.image("${docker_registry_no_http}/${distro}:${docker_tag}"),
                    pull: true,
                    args: [
                        "--name ${container_name}",
                        " --hostname ${distro}",
                    ],
                ) {
                    versioning.print_image_tag();
                    sh("make .venv");
                    withCredentials([
                        usernamePassword(
                            credentialsId: 'nexus',
                            passwordVariable: 'NEXUS_PASSWORD',
                            usernameVariable: 'NEXUS_USERNAME'),
                    ]) {
                        /// Don't use withEnv, see
                        /// https://issues.jenkins.io/browse/JENKINS-43632
                        sh("${omd_env_vars.join(' ')} make -C omd ${package_type}");
                    }

                    package_name = cmd_output("ls check-mk-${edition}-${cmk_version}*.${package_type}");
                    if (!package_type) {
                        error("No package 'check-mk-${edition}-${cmk_version}*.${package_type}' found in ${checkout_dir}")
                    }
                }
            }
        }
    }

    inside_container(ulimit_nofile: 1024) {
        stage("Sign package") {
            package_helper.sign_package(
                checkout_dir,
                "${checkout_dir}/${package_name}"
            );
        }

        stage("Test package") {
            package_helper.test_package(
                "${checkout_dir}/${package_name}",
                distro, WORKSPACE,
                checkout_dir,
                cmk_version
            );
        }
    }

    stage("Parse cache hits") {
        bazel_logs.try_parse_bazel_execution_log(distro, checkout_dir, bazel_log_prefix);
    }

    stage("Archive stuff") {
        dir("${checkout_dir}") {
            setCustomBuildProperty(
                key: "path_hashes",
                value: versioning.path_hashes(["."])
            );
            show_duration("archiveArtifacts") {
                archiveArtifacts(
                    artifacts: "*.deb, *.rpm, *.cma, ${bazel_log_prefix}*, omd/bill-of-materials.json",
                    fingerprint: true,
                );
            }
        }
    }
}

return this;
