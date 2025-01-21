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
    ]);

    check_environment_variables([
        "ARTIFACT_STORAGE",
        "NEXUS_ARCHIVES_URL",
    ]);

    def versioning = load("${checkout_dir}/buildscripts/scripts/utils/versioning.groovy");
    def all_distros = versioning.get_distros(override: "all")
    def distros = versioning.get_distros(edition: "all", use_case: "all", override: OVERRIDE_DISTROS);

    def vers_tag = versioning.get_docker_tag(scm, checkout_dir);
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


    withCredentials([
        usernamePassword(
            credentialsId: 'nexus',
            usernameVariable: 'USERNAME',
            passwordVariable: 'PASSWORD')
    ]) {
        def alias_names = [:];
        def image_ids = [:];
        def dockerfiles = [:];

        dir("${checkout_dir}") {
            distros.each { distro ->
                dockerfiles[distro] = "${distro}/Dockerfile";
                alias_names[distro] = cmd_output(
                    "grep 'ARG IMAGE_' " +
                    "buildscripts/infrastructure/build-nodes/${dockerfiles[distro]}" +
                    " | awk '{print \$2}'").replaceAll("[\r\n]+", "");
                image_ids[distro] = resolve_docker_image_alias(alias_names[distro]);
            }
            sh("""
                cp defines.make static_variables.bzl package_versions.bzl .bazelversion omd/strip_binaries \
                buildscripts/infrastructure/build-nodes/scripts

                cp omd/distros/*.mk buildscripts/infrastructure/build-nodes/scripts
            """);
        }

        println("alias_names: ${alias_names}");
        println("dockerfiles: ${dockerfiles}");
        println("image_ids: ${image_ids}");

        dir("${checkout_dir}/buildscripts/infrastructure/build-nodes") {
            def stages = distros.collectEntries { distro ->
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
                        def docker_build_args = (""
                            + " --build-arg ${alias_names[distro]}=${image_ids[distro]}"

                            + " --build-arg DOCKER_REGISTRY='${docker_registry_no_http}'"
                            + " --build-arg NEXUS_ARCHIVES_URL='${NEXUS_ARCHIVES_URL}'"
                            + " --build-arg DISTRO='${distro}'"
                            + " --build-arg NEXUS_USERNAME='${USERNAME}'"
                            + " --build-arg NEXUS_PASSWORD='${PASSWORD}'"
                            + " --build-arg ARTIFACT_STORAGE='${ARTIFACT_STORAGE}'"

                            + " --build-arg VERS_TAG='${vers_tag}'"
                            + " --build-arg BRANCH_VERSION='${branch_version}'"
                            + " -f ${dockerfiles[distro]} ."
                        );

                        if (params.BUILD_IMAGE_WITHOUT_CACHE) {
                            docker_build_args = "--no-cache " + docker_build_args;
                        }

                        println("Build: ${image_name} with: ${docker_build_args}");
                        image = docker.build(image_name, docker_build_args);
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
    }
}

return this;
