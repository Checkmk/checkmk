#!groovy

/// file: build-build-image.groovy

// groovylint-disable MethodSize
void main() {
    check_job_parameters([
        "BUILD_IMAGE_WITHOUT_CACHE",
        "CIPARAM_OVERRIDE_DOCKER_TAG_BUILD",
        "DISTRO",
        "PUBLISH_IMAGES",
    ]);

    check_environment_variables([
        "ARTIFACT_STORAGE",
        "NEXUS_ARCHIVES_URL",
    ]);

    def package_helper = load("${checkout_dir}/buildscripts/scripts/utils/package_helper.groovy");
    def versioning = load("${checkout_dir}/buildscripts/scripts/utils/versioning.groovy");

    def all_distros = [];
    def distro = "";
    def safe_branch_name = versioning.safe_branch_name();
    def branch_version = versioning.get_branch_version(checkout_dir);
    inside_container_minimal(safe_branch_name: safe_branch_name) {
        all_distros = versioning.get_distros(override: "all")
        distro = versioning.get_distros(edition: "all", use_case: "all", override: params.DISTRO);
        if (distro.size() == 1) {
            distro = distro[0];
        } else {
            raise("This is a SINGLE distro building job, can not build for ${distro.size()}: ${distro}");
        }
    }

    def vers_tag = params.CIPARAM_OVERRIDE_DOCKER_TAG_BUILD ?: versioning.get_docker_tag(checkout_dir);
    def publish_images = params.PUBLISH_IMAGES == true;

    def branch_base_folder = package_helper.branch_base_folder(true);
    def distro_base_image_id = "";
    def docker_build_args = "";
    def image_name = "";
    // the following images are special ones required for k8s
    def special_image_details = [
        "minimal-alpine-bash-git": [
            "tag_name": "minimal-alpine-bash-git",
            "image_alias_name": "IMAGE_ALPINE_3_22",
            "docker_file_path": "buildscripts/infrastructure/build-nodes/bootstrap/Dockerfile",
        ],
        "minimal-ubuntu-checkmk": [
            "tag_name": "minimal-ubuntu-checkmk-${safe_branch_name}",
            "image_alias_name": "IMAGE_UBUNTU_24_04",
            "docker_file_path": "buildscripts/infrastructure/build-nodes/minimal/Dockerfile",
        ],
        "minimal-alpine-python-checkmk": [
            "tag_name": "minimal-alpine-python-checkmk-${safe_branch_name}",
            "image_alias_name": "IMAGE_PYTHON_3_14",
            "docker_file_path": "buildscripts/scripts/Dockerfile",
        ],
    ];
    def tag_suffix = branch_base_folder.startsWith("Testing") ? "-testing" : "";

    print(
        """
        |===== CONFIGURATION ===============================
        |all_distros:.............. │${all_distros}│
        |distro:................... │${distro}│
        |publish_images:........... │${publish_images}│
        |vers_tag:................. │${vers_tag}│
        |safe_branch_name:......... │${safe_branch_name}│
        |branch_version:........... │${branch_version}│
        |===================================================
        """.stripMargin());

    currentBuild.description += (
        """
        |Building for the following Distro: ${distro}
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
        smart_stage(
            name: "Build ${distro}",
            raiseOnError: true,
        ) {
            if (distro in all_distros) {
                def real_distro_name = "";
                dir("${checkout_dir}") {
                    inside_container_minimal(safe_branch_name: safe_branch_name) {
                        real_distro_name = cmd_output(
                            "basename \$(realpath buildscripts/infrastructure/build-nodes/${distro})"
                        );
                        // if "kubernetes_inherit_from" is not UNSET, the script will be called with "--no-docker"
                        distro_base_image_id = resolve_docker_image_alias(
                            "IMAGE_${real_distro_name.toUpperCase().replaceAll('\\.', '_').replaceAll('-', '_')}"
                        );
                    }
                }

                image_name = "${distro}:${vers_tag}${tag_suffix}";
                def distro_mk_file_name = "${real_distro_name.toUpperCase().replaceAll('-', '_')}.mk";

                docker_build_args = (""
                    + " --build-arg DISTRO_IMAGE_BASE='${distro_base_image_id}'"
                    + " --build-arg DISTRO_MK_FILE='${distro_mk_file_name}'"
                    + " --build-arg DISTRO='${distro}'"
                    + " --build-arg VERS_TAG='${vers_tag}'"
                    + " --build-arg BRANCH_VERSION='${branch_version}'"

                    + " --build-arg DOCKER_REGISTRY='${docker_registry_no_http}'"
                    + " --build-arg NEXUS_ARCHIVES_URL='${env.NEXUS_ARCHIVES_URL}'"
                    + " --build-arg NEXUS_USERNAME='${NEXUS_USERNAME}'"
                    + " --build-arg NEXUS_PASSWORD='${NEXUS_PASSWORD}'"
                    + " --build-arg ARTIFACT_STORAGE='${env.ARTIFACT_STORAGE}'"

                    + " --dockerfile 'buildscripts/infrastructure/build-nodes/${distro}/Dockerfile'"
                    + " --context temp-build-context"

                    + " --destination ${docker_registry_no_http}/${image_name}"
                );

                if ((safe_branch_name ==~ /master|\d\.\d\.\d/) && ("${params.CIPARAM_OVERRIDE_DOCKER_TAG_BUILD}" == "")) {
                    docker_build_args += " --destination ${docker_registry_no_http}/${distro}:${safe_branch_name}-latest${tag_suffix}"
                }
            } else if (distro in special_image_details) {
                def details = special_image_details[distro];
                inside_container_minimal(safe_branch_name: safe_branch_name) {
                    distro_base_image_id = resolve_docker_image_alias(details.image_alias_name);
                }

                image_name = "${details.tag_name}${tag_suffix}"

                docker_build_args = (""
                    + " --build-arg IMAGE_BASE='${distro_base_image_id}'"

                    + " --build-arg DOCKER_REGISTRY='${docker_registry_no_http}'"
                    + " --build-arg NEXUS_ARCHIVES_URL='${env.NEXUS_ARCHIVES_URL}'"
                    + " --build-arg NEXUS_USERNAME='${NEXUS_USERNAME}'"
                    + " --build-arg NEXUS_PASSWORD='${NEXUS_PASSWORD}'"
                    + " --build-arg ARTIFACT_STORAGE='${env.ARTIFACT_STORAGE}'"

                    + " --dockerfile '${details.docker_file_path}'"
                    + " --context ./"

                    + " --destination ${docker_registry_no_http}/${image_name}"
                    + " --destination ${docker_registry_no_http}/${details.tag_name}:latest${tag_suffix}"
                );
            } else if (distro == "testing-image") {
                // use the a few moments earlier built image
                def testing_distro = "ubuntu-22.04";
                def tag_name = "testing-${testing_distro}-checkmk-${safe_branch_name}";
                image_name = "${testing_distro}:${safe_branch_name}-latest";
                distro_base_image_id = "${docker_registry_no_http}/${image_name}";

                docker_build_args = (""
                    + " --build-arg IMAGE_BASE='${distro_base_image_id}'"
                    + " --build-arg DISTRO='${testing_distro}'"

                    + " --dockerfile 'buildscripts/infrastructure/build-nodes/testing/Dockerfile'"
                    + " --context temp-build-context"

                    + " --destination ${docker_registry_no_http}/${image_name}"
                    + " --destination ${docker_registry_no_http}/${tag_name}:latest${tag_suffix}"
                );
            } else {
                raise("Unknown distro: ${distro}");
            }

            if (params.BUILD_IMAGE_WITHOUT_CACHE) {
                println("No cache is used for building ${image_name}");
            } else {
                docker_build_args += " --cache-run-layers --cache-copy-layers";
            }

            if (publish_images) {
                // make it more robust to outages or overload situations
                docker_build_args += " --push-retry 3";
            } else {
                docker_build_args += " --no-push";
                println("Skipping upload for ${image_name}");
            }

            println("docker_build_args: ${docker_build_args}");

            dir("${checkout_dir}") {
                container("kaniko-alpine") {
                    // as soon as the container is left, the docker config file is gone
                    // create the docker auth file
                    /* groovylint-disable LineLength */
                    sh("""#!/bin/sh
                        echo '{"auths":{"${docker_registry_no_http}":{"username":"${NEXUS_USERNAME}","password":"${NEXUS_PASSWORD}"}}}' > /kaniko/.docker/config.json
                    """);
                    /* groovylint-enable LineLength */

                    sh("""#!/bin/sh
                        /kaniko/executor ${docker_build_args}
                    """);
                }
            }
        }
    }
}

return this;
