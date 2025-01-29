#!groovy

/// file: build-build-images.groovy

/// Build base images on top of (pinned) upstream OS images

/// Parameters / environment values:
///
/// Jenkins artifacts: ???
/// Other artifacts: ???
/// Depends on: image aliases for upstream OS images on Nexus, ???

import org.jenkinsci.plugins.pipeline.modeldefinition.Utils

def main() {
    check_job_parameters([
        "SYNC_WITH_IMAGES_WITH_UPSTREAM",
        "PUBLISH_IMAGES",
        "OVERRIDE_DISTROS",
        "BUILD_IMAGE_WITHOUT_CACHE",
        "CIPARAM_OVERRIDE_DOCKER_TAG_BUILD",
    ]);

    check_environment_variables([
        "ARTIFACT_STORAGE",
        "NEXUS_ARCHIVES_URL",
    ]);

    def versioning = load("${checkout_dir}/buildscripts/scripts/utils/versioning.groovy");
    def all_distros = versioning.get_distros(override: "all")
    def distros = versioning.get_distros(edition: "all", use_case: "all", override: OVERRIDE_DISTROS);

    def vers_tag = params.CIPARAM_OVERRIDE_DOCKER_TAG_BUILD ?: versioning.get_docker_tag(scm, checkout_dir);
    def safe_branch_name = versioning.safe_branch_name(scm);
    def branch_version = versioning.get_branch_version(checkout_dir);
    def publish_images = PUBLISH_IMAGES=='true';  // FIXME should be case sensitive

    print(
        """
        |===== CONFIGURATION ===============================
        |all_distros:....................(local)  │${all_distros}│
        |distros:........................(local)  │${distros}│
        |publish_images:.................(local)  │${publish_images}│
        |vers_tag:.......................(local)  │${vers_tag}│
        |safe_branch_name:...............(local)  │${safe_branch_name}│
        |branch_version:.................(local)  │${branch_version}│
        |===================================================
        """.stripMargin());

    currentBuild.description += (
        """
        |Building for the following Distros:
        |${distros}
        |""".stripMargin());

    stage("Prepare workspace") {
        dir("${checkout_dir}") {
            sh("""
                rm -rf temp-build-context
                mkdir temp-build-context
                defines/dev-images/populate-build-context.sh temp-build-context
            """);
        }
    }

    withCredentials([
        usernamePassword(
            credentialsId: 'nexus',
            usernameVariable: 'NEXUS_USERNAME',
            passwordVariable: 'NEXUS_PASSWORD')
    ]) {
        def distro_base_image_id = [:];
        def real_distro_name = [:];

        stage("Provide\nupstream images") {
            dir("${checkout_dir}") {
                distro_base_image_id = distros.collectEntries { distro -> [
                    (distro) : {
                        real_distro_name[distro] = cmd_output(
                            "basename \$(realpath buildscripts/infrastructure/build-nodes/${distro})");
                        resolve_docker_image_alias(
                            "IMAGE_${real_distro_name[distro].toUpperCase().replaceAll('\\.', '_').replaceAll('-', '_')}")
                    }()
                ]};
            }
        }

        def stages = all_distros.collectEntries { distro ->
            [("${distro}") : {
                def run_condition = distro in distros;
                def image = false;

                /// this makes sure the whole parallel thread is marked as skipped
                if (! run_condition){
                    Utils.markStageSkippedForConditional("${distro}");
                }

                smart_stage(
                    name: "Build ${distro}",
                    condition: run_condition,
                    raiseOnError: true,
                ) {
                    def image_name = "${distro}:${vers_tag}";
                    def distro_mk_file_name = "${real_distro_name[distro].toUpperCase().replaceAll('-', '_')}.mk";
                    def docker_build_args = (""
                        + " --build-arg DISTRO_IMAGE_BASE='${distro_base_image_id[distro]}'"
                        + " --build-arg DISTRO_MK_FILE='${distro_mk_file_name}'"
                        + " --build-arg DISTRO='${distro}'"
                        + " --build-arg VERS_TAG='${vers_tag}'"
                        + " --build-arg BRANCH_VERSION='${branch_version}'"

                        + " --build-arg DOCKER_REGISTRY='${docker_registry_no_http}'"
                        + " --build-arg NEXUS_ARCHIVES_URL='${NEXUS_ARCHIVES_URL}'"
                        + " --build-arg NEXUS_USERNAME='${NEXUS_USERNAME}'"
                        + " --build-arg NEXUS_PASSWORD='${NEXUS_PASSWORD}'"
                        + " --build-arg ARTIFACT_STORAGE='${ARTIFACT_STORAGE}'"

                        + " -f 'buildscripts/infrastructure/build-nodes/${distro}/Dockerfile'"
                        + " temp-build-context"
                    );

                    if (params.BUILD_IMAGE_WITHOUT_CACHE) {
                        docker_build_args = "--no-cache " + docker_build_args;
                    }
                    dir("${checkout_dir}") {
                        image = docker.build(image_name, docker_build_args);
                    }
                }

                smart_stage(
                    name: "Upload ${distro}",
                    condition: run_condition && publish_images,
                    raiseOnError: true,
                ) {
                    docker.withRegistry(DOCKER_REGISTRY, "nexus") {
                        image.push();
                        if (safe_branch_name ==~ /master|\d\.\d\.\d/) {
                            image.push("${safe_branch_name}-latest");
                        }
                    }
                }
            }]
        }
        currentBuild.result = parallel(stages).values().every { it } ? "SUCCESS" : "FAILURE";
    }

    /// build and use reference image in order to check if it's working at all
    /// and to fill caches. Also do some tests in order to check if permissions
    /// are fine and everything gets cleaned up
    stage("Use reference image") {
        dir("${checkout_dir}") {
            /// First check the bash script, since it yields more useful log output
            /// in erroneous cases
            show_duration("check reference image") {
                sh("""
                    POPULATE_BUILD_CACHE=1 \
                    VERBOSE=1 \
                    PULL_BASE_IMAGE=1 \
                    ${checkout_dir}/scripts/run-in-docker.sh cat /etc/os-release
                """);
            }
            /// also check the default way to use a container
            inside_container() {
                sh("""
                    echo Hello from reference image
                    cat /etc/os-release
                    echo \$USER
                    echo \$HOME
                    echo Hello from reference image
                    cat /etc/os-release
                    echo \$USER
                    echo \$HOME
                    ls -alF \$HOME
                    ls -alF \$HOME/.cache
                    echo fcache > \$HOME/.cache/fcache
                    ls -alF ${checkout_dir}/shared_cargo_folder
                    echo fcargo > ${checkout_dir}/shared_cargo_folder/fcargo
                """);
                sh("git status");
            }
            /// also test the run-in-docker.sh script
            sh("""
                ${checkout_dir}/scripts/run-in-docker.sh cat /etc/os-release
            """);
        }
    }
}

return this;
