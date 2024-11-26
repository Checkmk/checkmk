#!groovy

/// file: test-laptop-setup.groovy

/// Install required packages for Checkmk development

/// Parameters / environment values:
///
/// Jenkins artifacts: ???
/// Other artifacts: ???
/// Depends on: image aliases for upstream OS images on Nexus, ???

def main() {
    check_environment_variables([
        "NEXUS_ARCHIVES_URL",
    ]);

    def versioning = load("${checkout_dir}/buildscripts/scripts/utils/versioning.groovy");

    def safe_branch_name = versioning.safe_branch_name(scm);
    def branch_version = versioning.get_branch_version(checkout_dir);

    print(
        """
        |===== CONFIGURATION ===============================
        |safe_branch_name:...............(local)  │${safe_branch_name}│
        |branch_version:.................(local)  │${branch_version}│
        |===================================================
        """.stripMargin());

    withCredentials([
        usernamePassword(
            credentialsId: 'nexus',
            usernameVariable: 'USERNAME',
            passwordVariable: 'PASSWORD')
    ]) {
        def DOCKER_ARGS = (
            " --no-cache" +
            " --build-arg NEXUS_ARCHIVES_URL='$NEXUS_ARCHIVES_URL'" +
            " --build-arg NEXUS_USERNAME='$USERNAME'" +
            " --build-arg NEXUS_PASSWORD='$PASSWORD'" +
            " --build-arg CI=1"
        );
        // no support for 20.04, sorry
        // python2 would be required, and the system Python does not support typing in "strip_binaries"
        def ubuntu_versions = ["22.04", "24.04"];

        dir("${checkout_dir}") {
            sh("""
                cp \
                    .bazelversion \
                    defines.make \
                    omd/strip_binaries \
                    omd/distros/*.mk \
                    package_versions.bzl \
                buildscripts/infrastructure/build-nodes/scripts
            """);
        }

        dir("${checkout_dir}/buildscripts/infrastructure/build-nodes") {
            def stages = ubuntu_versions.collectEntries { distro ->
                [("${distro}") : {
                    stage("Build ${distro}") {
                        def THIS_DOCKER_ARGS = DOCKER_ARGS + (
                            " --build-arg DISTRO='ubuntu-${distro}'" +
                            " --build-arg BASE_IMAGE='ubuntu:${distro}'" +
                            " -f laptops/Dockerfile ."
                        );
                        print(THIS_DOCKER_ARGS);

                        docker.build("test-install-development:${safe_branch_name}-latest", THIS_DOCKER_ARGS);
                    }
                }];
            }
            parallel(stages);
        }
    }
}

return this;
