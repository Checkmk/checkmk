#!groovy

/// file: unpublish-container-image.groovy

void main() {
    // Check for required job params
    check_job_parameters([
        "EDITION",
        "VERSION",
        "DRY_RUN",  // making sure the param exists
    ]);

    currentBuild.description += (
        """
        |Run composition tests for<br>
        |ACTION: ${params.ACTION}<br>
        |EDITION: ${params.EDITION}<br>
        |DRY_RUN: ${params.DRY_RUN}<br>
        |TAG_TO_DELETE: ${params.TAG_TO_DELETE}<br>
        """.stripMargin());

    def helper = load("${checkout_dir}/buildscripts/scripts/utils/test_helper.groovy");

    stage("Remove image") {
        inside_container(
            set_docker_group_id: true,
            mount_credentials: true,
        ) {
            withCredentials([
                usernamePassword(
                    credentialsId: helper.registry_credentials_id(params.EDITION),
                    passwordVariable: 'DOCKER_PASSPHRASE',
                    usernameVariable: 'DOCKER_USERNAME'),
                usernamePassword(
                    credentialsId: 'nexus',
                    passwordVariable: 'NEXUS_PASSWORD',
                    usernameVariable: 'NEXUS_USERNAME'),
            ]) {
                withEnv(["PYTHONUNBUFFERED=1"]) {
                    dir("${checkout_dir}") {
                        def command = """scripts/run-uvenv \
                        buildscripts/scripts/unpublish-container-image.py \
                        --editions_file editions.yml --edition ${params.EDITION} \
                        ${params.ACTION}
                        """;

                        if (params.ACTION == "delete") {
                            if (params.DRY_RUN) {
                                command += " --dry-run";
                            }

                            command += " --image-tag ${params.TAG_TO_DELETE}";
                        }

                        sh(script: command);
                    }
                }
            }
        }
    }
}

return this;
