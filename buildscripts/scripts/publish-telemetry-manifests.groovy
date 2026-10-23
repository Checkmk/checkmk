#!groovy

/// file: publish-telemetry-manifests.groovy

// Builds the telemetry manifests and uploads them to the web servers, where
// they are used to generate the telemetry information pages.

void main() {
    def versioning = load("${checkout_dir}/buildscripts/scripts/utils/versioning.groovy");

    def branch_version = versioning.get_branch_version(checkout_dir);
    def target_dir = "/home/mkde/telemetry";
    def manifests = [
        // [bazel target, published file name]
        [
            "//non-free/packages/cmk-mcp:telemetry_manifest",
            "mcp_${branch_version}.json",
        ],
    ];
    def manifest_files = manifests.collect { manifest -> manifest[1] };
    def targets_credentials = [
        [env.WEB_STAGING, "web-staging"],
        ["checkmk.com", "checkmk-deploy"],
    ];

    print(
        """
        |===== CONFIGURATION ===============================
        |checkout_dir:............. │${checkout_dir}│
        |branch_version:........... │${branch_version}│
        |target_dir:............... │${target_dir}│
        |===================================================
        """.stripMargin());

    dir(checkout_dir) {
        inside_container() {
            stage("Build telemetry manifests") {
                manifests.each { manifest ->
                    def target = manifest[0];
                    def file_name = manifest[1];
                    /* groovylint-disable LineLength */
                    sh("""
                        bazel build ${target}
                        output="\$(bazel info workspace)/\$(bazel cquery ${target} --output=starlark --starlark:expr='target.files.to_list()[0].path')"
                        cp -f "\${output}" ${file_name}
                        chmod 644 ${file_name}
                    """);
                    /* groovylint-enable LineLength */
                }
                archiveArtifacts(
                    artifacts: manifest_files.join(","),
                    fingerprint: true,
                );
            }

            targets_credentials.each { target_credential ->
                def target = target_credential[0];
                def credentials_id = target_credential[1];

                stage("Upload telemetry manifests to ${target}") {
                    withCredentials([
                        sshUserPrivateKey(
                            credentialsId: credentials_id,
                            keyFileVariable: 'SSH_KEYFILE',
                            usernameVariable: 'SSH_USER',
                        )
                    ]) {
                        sh("""
                            rsync --verbose \
                                -e "ssh -o StrictHostKeyChecking=no -i \$SSH_KEYFILE -p ${WEB_STAGING_PORT}" \
                                ${manifest_files.join(" ")} \
                                "\${SSH_USER}@${target}:${target_dir}/"
                        """);
                    }
                }
            }
        }
    }
}

return this;
