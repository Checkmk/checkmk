#!groovy

/// file: build-cloud-images.groovy

/// Builds cloud images using checkmk (AWS and Azure)

/// Parameters / environment values:
///     EDITION: cloud only currently
///
/// Jenkins artifacts: will be directly pushed into the cloud
/// Depends on: Ubuntu 22.04 package beeing available on download.checkmk.com (will be fetched by ansible collection)

def main() {
    check_job_parameters([
        "EDITION",
        "VERSION",
    ])

    if (EDITION != 'cloud') {
        error "The AMI/Azure builds must currently *only* use the cloud edition."
    }

    def versioning = load("${checkout_dir}/buildscripts/scripts/utils/versioning.groovy")
    def cmk_version = versioning.get_cmk_version(versioning.safe_branch_name(scm), VERSION)
    if (cmk_version != versioning.strip_rc_number_from_version(cmk_version)) {
        error "You may try to build a release candidate (${cmk_version}) for the cloud images but " +
            "this is currently not supported. During a release, we will build the cloud images when a package rc was " +
            "tested to be OK."
    }
    shout("Building cloud images for version: ${cmk_version}")

    def version_suffix = "${cmk_version}-build-${env.BUILD_NUMBER}"
    def env_secret_map = build_env_secret_map(cmk_version, version_suffix)
    def cloud_targets = ["amazon-ebs", "azure-arm"]

    currentBuild.description = (
        """
        |Building the Cloud images
        |""".stripMargin())


    stage('Cleanup') {
        dir("${checkout_dir}") {
            sh("git clean -xdf")
        }
    }

    docker.withRegistry(DOCKER_REGISTRY, 'nexus') {
        docker_image_from_alias("IMAGE_TESTING").inside() {
            stage('Packer init') {
                dir("${checkout_dir}/packer") {
                    // This step cannot be done during building images as it needs the *.pkr.hcl scripts from the repo
                    sh("packer init .")
                }
            }
            parallel(create_stages(cloud_targets, env_secret_map));
        }
    }
}

def build_env_secret_map(cmk_version, version_suffix) {
    return [
        "env"    : [
            // ~~~ COMMON ~~~
            "PKR_VAR_cmk_version=${cmk_version}",
            // ~~~ QUEMU ~~~
            "PKR_VAR_qemu_output_dir_name=cmk",
            // ~~~ AWS ~~~
            "PKR_VAR_aws_ami_name=cmk-ami-https-${version_suffix}",
            // ~~~ AZURE ~~~
            "PKR_VAR_azure_resource_group=rg-packer-dev-weu",
            "PKR_VAR_azure_build_resource_group_name=rg-packer-dev-weu",
            "PKR_VAR_azure_virtual_network_resource_group_name=rg-spokes-network-weu",
            "PKR_VAR_azure_virtual_network_name=vnet-spoke-packer-dev-weu",
            "PKR_VAR_azure_virtual_network_subnet_name=snet-spoke-packer-dev-default-weu",
            "PKR_VAR_azure_image_name=cmk-azure-${version_suffix}"
        ],
        "secrets": [
            // ~~~ COMMON ~~~
            usernamePassword(
                credentialsId: 'cmk-credentials',
                passwordVariable: 'PKR_VAR_cmk_download_pass',
                usernameVariable: 'PKR_VAR_cmk_download_user'),
            // ~~~ AWS ~~~
            string(
                credentialsId: 'aws_secret_key',
                variable: 'PKR_VAR_aws_secret_key'),
            string(
                credentialsId: 'aws_access_key',
                variable: 'PKR_VAR_aws_access_key'),
            // ~~~ AZURE ~~~
            usernamePassword(
                credentialsId: 'azure_client',
                passwordVariable: 'PKR_VAR_azure_client_secret',
                usernameVariable: 'PKR_VAR_azure_client_id'),
            string(
                credentialsId: 'azure_subscription_id',
                variable: 'PKR_VAR_azure_subscription_id'),
            string(
                credentialsId: 'azure_tenant_id',
                variable: 'PKR_VAR_azure_tenant_id'),
        ],
    ]

}

def create_stages(cloud_targets, env_secret_map) {
    return cloud_targets.collectEntries { target ->
        [("${target}"): {
            stage("Building target ${target}") {
                withCredentials(env_secret_map["secrets"]) {
                    withEnv(env_secret_map["env"]) {
                        dir("${checkout_dir}/packer") {
                            sh("""
                                   packer build -only="checkmk-ansible.${target}.builder" .;
                            """)
                            }
                        }
                    }
                }
            }
        ]
    }
}

return this
