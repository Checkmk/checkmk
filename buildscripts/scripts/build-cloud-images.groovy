#!groovy

/// file: build-cloud-images.groovy

/// Builds cloud images using checkmk (AWS and Azure)

/// Parameters / environment values:
///     EDITION: cloud only currently
///
/// Jenkins artifacts: will be directly pushed into the cloud
/// Depends on: Ubuntu 22.04 package beeing available on download.checkmk.com (will be fetched by ansible collection)

def build_cloud_images_names(version) {
    def version_suffix = "${version}-build-${env.BUILD_NUMBER}";
    return ["cmk-ami-https-${version_suffix}", "cmk-azure-${version_suffix}"]
}

def main() {
    check_job_parameters([
        "EDITION",
        "VERSION",
        "BUILD_CLOUD_IMAGES",
        "PUBLISH_IN_MARKETPLACE",
    ])

    if (EDITION != 'cloud') {
        error("The AMI/Azure builds must currently *only* use the cloud edition.");
    }

    def versioning = load("${checkout_dir}/buildscripts/scripts/utils/versioning.groovy")
    def branch_version = versioning.get_branch_version(checkout_dir);
    def cmk_version = versioning.get_cmk_version(versioning.safe_branch_name(), branch_version, VERSION)
    if (cmk_version != versioning.strip_rc_number_from_version(cmk_version)) {
        error("You may try to build a release candidate (${cmk_version}) for the cloud images but " +
            "this is currently not supported. During a release, we will build the cloud images when a package rc was " +
            "tested to be OK.");
    }
    def ami_image_name = build_cloud_images_names(cmk_version)[0];
    def azure_image_name = build_cloud_images_names(cmk_version)[1];
    def env_secret_map = build_env_secret_map(cmk_version, ami_image_name, azure_image_name)
    def cloud_targets = ["amazon-ebs", "azure-arm"]
    def build_cloud_images = params.BUILD_CLOUD_IMAGES
    def publish_cloud_images = params.PUBLISH_IN_MARKETPLACE
    def packer_envvars = ['CHECKPOINT_DISABLE=1', "PACKER_CONFIG_DIR=${checkout_dir}/packer/.packer"]

    currentBuild.description += (
        """
        |Building the Cloud images
        |""".stripMargin());


    stage('Cleanup') {
        dir("${checkout_dir}") {
            sh("git clean -xdf");
        }
    }

    // Build Phase
    inside_container() {
        smart_stage(
            name: 'Packer init',
            condition: build_cloud_images,
            raiseOnError: true,
        ) {
            dir("${checkout_dir}/packer") {
                // https://developer.hashicorp.com/packer/docs/configure#environment-variables-usable-for-packer
                withEnv(packer_envvars){
                    // This step cannot be done during building images as it needs the *.pkr.hcl scripts from the repo
                    sh("packer init .");
                }
            }
            parallel(create_build_stages(cloud_targets, env_secret_map, build_cloud_images, packer_envvars));
        }
    }

    // Publish Phase
    inside_container() {
        dir("${checkout_dir}") {
            // As we're using the same .venv for multiple cloud targets in parallel, we need to make sure the
            // .venv is up-to-date before parallelisation. Otherwise one process may fail due to a invalid .venv.
            sh("make .venv");
            parallel(create_publish_stages(["aws": ami_image_name, "azure": azure_image_name], cmk_version, publish_cloud_images))
        }
    }
}

def build_env_secret_map(cmk_version, ami, azure) {
    return [
        "env"    : [
            // ~~~ COMMON ~~~
            "PKR_VAR_cmk_version=${cmk_version}",
            // ~~~ QUEMU ~~~
            "PKR_VAR_qemu_output_dir_name=cmk",
            // ~~~ AWS ~~~
            "PKR_VAR_aws_ami_name=${ami}",
            // ~~~ AZURE ~~~
            "PKR_VAR_azure_resource_group=rg-packer-dev-weu",
            "PKR_VAR_azure_build_resource_group_name=rg-packer-dev-weu",
            "PKR_VAR_azure_virtual_network_resource_group_name=rg-spokes-network-weu",
            "PKR_VAR_azure_virtual_network_name=vnet-spoke-packer-dev-weu",
            "PKR_VAR_azure_virtual_network_subnet_name=snet-spoke-packer-dev-default-weu",
            "PKR_VAR_azure_image_name=${azure}"
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
    ];
}

def create_build_stages(cloud_targets, env_secret_map, build_images, packer_envvars) {
    return cloud_targets.collectEntries { target ->
        [("Building target ${target}"): {
            smart_stage(
                name: "Building target ${target}",
                condition: build_images,
                raiseOnError: true,
            ) {
                withCredentials(env_secret_map["secrets"]) {
                    withEnv(env_secret_map["env"] + packer_envvars) {
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

def create_publish_stages(targets_names, version, publish) {
    return targets_names.collectEntries { target, name ->
        [("Publish ${target} in marketplace"): {
            smart_stage(
                name: 'Publish in marketplace',
                condition: publish,
                raiseOnError: true
            ) {
                withEnv(["AWS_DEFAULT_REGION=us-east-1", "PYTHONUNBUFFERED=1", "AZURE_RESOURCE_GROUP=rg-packer-dev-weu"]) {
                    withCredentials([
                        string(
                            credentialsId: 'aws_publisher_secret_key',
                            variable: 'AWS_SECRET_ACCESS_KEY'),
                        string(
                            credentialsId: 'aws_publisher_access_key',
                            variable: 'AWS_ACCESS_KEY_ID'),
                        usernamePassword(
                            credentialsId: 'azure_client',
                            passwordVariable: 'AZURE_CLIENT_SECRET',
                            usernameVariable: 'AZURE_CLIENT_ID'),
                        string(
                            credentialsId: 'azure_subscription_id',
                            variable: 'SUBSCRIPTION_ID'),
                        string(
                            credentialsId: 'azure_tenant_id',
                            variable: 'AZURE_TENANT_ID'),
                    ]) {
                        // Used global env variable from jenkins:
                        // AWS_MARKETPLACE_SCANNER_ARN and AWS_AMI_IMAGE_PRODUCT_ID
                        sh("""
                           scripts/run-uvenv buildscripts/scripts/publish_cloud_images.py \
                            --cloud-type ${target} --new-version ${version} \
                            --build-tag '${env.JOB_BASE_NAME}-${env.BUILD_NUMBER}' --image-name ${name} \
                            --marketplace-scanner-arn '${AWS_MARKETPLACE_SCANNER_ARN}' \
                            --product-id '${AWS_AMI_IMAGE_PRODUCT_ID}' \
                            --azure-subscription-id '${SUBSCRIPTION_ID}' \
                            --azure-resource-group '${AZURE_RESOURCE_GROUP}';
                        """)
                        }
                    }
                }
            }
        ]
    }
}

return this;
