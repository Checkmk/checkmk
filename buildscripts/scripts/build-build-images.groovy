#!groovy

/// Build base images on top of (pinned) upstream OS images

/// Parameters / environment values:
///
/// Jenkins artifacts: ???
/// Other artifacts: ???
/// Depends on: image aliases for upstream OS images on Nexus, ???

def main() {
    global_dry_run_level = 0;

    check_job_parameters([
        "SYNC_WITH_IMAGES_WITH_UPSTREAM",
        "PUBLISH_IMAGES",
        "OVERRIDE_DISTROS",
    ]);

    check_environment_variables([
        "ARTIFACT_STORAGE",
        "NEXUS_ARCHIVES_URL",
    ]);

    def versioning = load("${checkout_dir}/buildscripts/scripts/utils/versioning.groovy");
    def distros = versioning.configured_or_overridden_distros("enterprise", OVERRIDE_DISTROS);

    def vers_tag = versioning.get_docker_tag(scm, checkout_dir);
    def branch_name = versioning.safe_branch_name(scm);
    def branch_version = versioning.get_branch_version(checkout_dir);
    def publish_images = PUBLISH_IMAGES=='true';  // FIXME should be case sensitive

    print(
        """
        |===== CONFIGURATION ===============================
        |distros:........................(local)  │${distros}│
        |publish_images:.................(local)  │${publish_images}│
        |vers_tag:.......................(local)  │${vers_tag}│
        |branch_name:....................(local)  │${branch_name}│
        |branch_version:.................(local)  │${branch_version}│
        |===================================================
        """.stripMargin());

    currentBuild.description = (
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
            sh("cp defines.make omd/strip_binaries buildscripts/infrastructure/build-nodes/scripts");
        }

        dir("${checkout_dir}/buildscripts/infrastructure/build-nodes") {
            // TODO: here it would be nice to iterate through all known distros
            //       and use a conditional_stage(distro in distros) approach
            def stages = distros.collectEntries { distro ->
                [("${distro}") : {
                        stage("Build ${distro}") {
                            on_dry_run_omit(GLOBAL_IMPACT, "docker.build(${distro}:${vers_tag})") {
                                def DOCKER_ARGS = (
                                    " --build-arg ${alias_names[distro]}=${image_ids[distro]}" +
                                    " --build-arg DOCKER_REGISTRY='${docker_registry_no_http}'" +
                                    " --build-arg NEXUS_ARCHIVES_URL='$NEXUS_ARCHIVES_URL'" +
                                    " --build-arg DISTRO='$distro'" +
                                    " --build-arg NEXUS_USERNAME='$USERNAME'" +
                                    " --build-arg NEXUS_PASSWORD='$PASSWORD'" +
                                    " --build-arg ARTIFACT_STORAGE='$ARTIFACT_STORAGE'" +
                                    " --build-arg VERS_TAG='$vers_tag'" +
                                    " --build-arg BRANCH_VERSION='$branch_version'" +
                                    " -f ${dockerfiles[distro]} .");
                                docker.build("${distro}:${vers_tag}", DOCKER_ARGS);
                            }
                        }}
                ]
            }
            def images = parallel(stages);

            conditional_stage('upload images', publish_images) {
                docker.withRegistry(DOCKER_REGISTRY, "nexus") {
                    images.each { distro, image ->
                        on_dry_run_omit(GLOBAL_IMPACT, "PUBLISH |${distro}|${image}|") {
                            image.push();
                            image.push("${branch_name}-latest");
                        }
                    }
                }
            }
        }
    }
}
return this;
