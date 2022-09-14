#!groovy
/// Build the Amazon Machine Image (AMI) for Checkmk

/// Parameters / environment values:
///     EDITION:
///
/// Jenkins artifacts: ???
/// Other artifacts: ???
/// Depends on: Ubuntu 20.04 / focal package

def main() {
    check_job_parameters([
        "EDITION",
        "VERSION",
        // "SET_LATEST_TAG",
        // FIXME this too? "SET_BRANCH_LATEST_TAG",
    ]);

    check_environment_variables([
        "WORKSPACE_TMP",
        "ARTIFACT_STORAGE",
        "NEXUS_ARCHIVES_URL",
    ]);

    def versioning = load("${checkout_dir}/buildscripts/scripts/utils/versioning.groovy");
    def artifacts_helper = load("${checkout_dir}/buildscripts/scripts/utils/upload_artifacts.groovy");

    def branch_name = versioning.safe_branch_name(scm);
    def branch_version = versioning.get_branch_version(checkout_dir);
    def cmk_version = versioning.get_cmk_version(branch_name, VERSION);

    if (EDITION != 'free') {
        error "The AMI build is currently only using the free edition.";
    }
    def package_dir = "${WORKSPACE_TMP}/download";
    def image_alias_name = "IMAGE_UBUNTU_22_04";
    def resolved_image_id = resolve_docker_image_alias(image_alias_name);

    currentBuild.description = (
        """
        |Building the Amazon Machine Image (AMI)
        |""".stripMargin());

    print(
        """
        |===== CONFIGURATION ===============================
        |image_alias_name:...............(local)  │${image_alias_name}│
        |resolved_image_id:..............(local)  │${resolved_image_id}│
        |package_dir:....................(local)  │${package_dir}│
        |===================================================
        """.stripMargin());

    stage('Cleanup') {
        cleanup_directory("${package_dir}");
        dir("${checkout_dir}") {
            sh("git clean -xdf");
        }
    }

    dir("${checkout_dir}/buildscripts/infrastructure/build-nodes") {
        sh('cp ../../../defines.make scripts');
        withCredentials([
            usernamePassword(
                credentialsId: 'nexus',
                usernameVariable: 'NEXUS_USERNAME',
                passwordVariable: 'NEXUS_PASSWORD')]) {

            artifacts_helper.download_deb(
                INTERNAL_DEPLOY_DEST,
                INTERNAL_DEPLOY_PORT,
                cmk_version,
                package_dir,
                EDITION,
                "focal",
            );

            stage('Build AMI')  {
                sh("ls -l ${checkout_dir}/buildscripts/infrastructure/build-nodes/aws")
                def DOCKER_ARGS = (
                    " --build-arg ${image_alias_name}=$resolved_image_id" +
                    " --build-arg DOCKER_REGISTRY='$docker_registry_no_http'" +
                    " --build-arg NEXUS_ARCHIVES_URL='$NEXUS_ARCHIVES_URL'" +
                    " --build-arg NEXUS_USERNAME='$NEXUS_USERNAME'" +
                    " --build-arg NEXUS_PASSWORD='$NEXUS_PASSWORD'" +
                    " --build-arg ARTIFACT_STORAGE='$ARTIFACT_STORAGE'" +
                    "  ${checkout_dir}/buildscripts/infrastructure/build-nodes/aws/");
                on_dry_run_omit(LONG_RUNNING, "Build Image") {
                    docker.build("build-image:ami_toolchain", DOCKER_ARGS).inside(
                        """-u 0:0 --ulimit nofile=1024:1024 \
                           -v ${package_dir}:/download \
                           -v /var/run/docker.sock:/var/run/docker.sock""") {
                        withCredentials([
                            usernamePassword(
                                credentialsId: 'aws',
                                passwordVariable: 'AWS_SECRET_ACCESS_KEY',
                                usernameVariable: 'AWS_ACCESS_KEY_ID'),
                            string(
                                credentialsId: 'ec2_key',
                                variable: 'EC2_KEY'),
                            sshUserPrivateKey(
                                credentialsId: 'ansible_ssh_private_key_file',
                                keyFileVariable: 'ANSIBLE_SSH_PRIVATE_KEY_FILE'),
                            string(
                                credentialsId: 'cmkadmin_pass',
                                variable: 'CMKADMIN_PASS'),
                        ]) {
                            /// NOTE: workaround 1):
                            /// "export DEFAULT_LOCAL_TMP" is required because ansible creates temporary
                            /// data in this directory if the variable DEFAULT_LOCAL_TMP is not specified
                            /// the temporary directory would be the root folder of the environment

                            /// NOTE:  workaround 2):
                            ///   HOME=$WORKSPACE_TMP must be set before running the ansible playbook
                            ///   otherwise the following error occurs, because ansible scripts
                            ///   access the environment variable HOME directly:
                            ///   Unable to create local directories /home/$HOME/.ansible/cp
                            try {
                                run_ansible("build_ami.yml", cmk_version);
                            } finally {
                                run_ansible("terminate_checkmk_ec2_instances.yml", cmk_version);
                            }
                        }
                    }
                }
            }
        }
    }
}

def run_ansible(playbook_file, cmk_version) {
    sh("printenv");
    dir("${checkout_dir}/buildscripts/infrastructure/build-nodes/aws") {
        sh("""
            export DEFAULT_LOCAL_TMP=/tmp &&
            export ANSIBLE_HOST_KEY_CHECKING=False &&
            HOME=$WORKSPACE_TMP \
            AWS_ACCESS_KEY_ID=$AWS_ACCESS_KEY_ID \
            AWS_SECRET_ACCESS_KEY=$AWS_SECRET_ACCESS_KEY \
            EC2_KEY=$EC2_KEY \
            ANSIBLE_SSH_PRIVATE_KEY_FILE=$ANSIBLE_SSH_PRIVATE_KEY_FILE \
            CMKADMIN_PASS=$CMKADMIN_PASS \
            PACKAGE_DIR=/download \
            EDITION=$EDITION \
            CMK_VERS=${cmk_version} \
            ./${playbook_file} -vvvv --ssh-common-args "-o ControlPath='/tmp/ansible-cp'"
        """);
    }
}
return this;
