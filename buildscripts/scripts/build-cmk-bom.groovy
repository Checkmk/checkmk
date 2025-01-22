#!groovy

/// file: build-cmk-bom.groovy

def main() {
    check_job_parameters([
        ["VERSION", true],
    ]);

    def versioning = load("${checkout_dir}/buildscripts/scripts/utils/versioning.groovy");

    def version = params.VERSION;
    def branch_version = versioning.get_branch_version(checkout_dir);

    /// Get the ID of the docker group from the node(!). This must not be
    /// executed inside the container (as long as the IDs are different)
    def docker_group_id = get_docker_group_id();

    print(
        """
        |===== CONFIGURATION ===============================
        |branch_version:........... │${branch_version}│
        |docker_group_id:.......... │${docker_group_id}│
        |===================================================
        """.stripMargin());

    dir("${WORKSPACE}/dependencyscanner") {
        def scanner_image;
        def relative_bom_path = "omd/bill-of-materials.json";
        def bom_path = "${checkout_dir}/${relative_bom_path}";

        stage("Prepare Dependencyscanner") {
            checkout([
                $class: 'GitSCM',
                branches: [[name: 'refs/heads/master']],
                browser: [
                    $class: 'GitWeb',
                    repoUrl: 'https://review.lan.tribe29.com/git/?p=dependencyscanner.git'
                ],
                userRemoteConfigs: [
                    [
                        credentialsId: '058f09c4-21c9-49ae-b72b-0b9d2f465da6',
                        url: 'ssh://jenkins@review.lan.tribe29.com:29418/dependencyscanner'
                    ]
                ],
            ]);
            scanner_image = docker.build("dependencyscanner", "--tag dependencyscanner .");
        }

        stage('Create BOM') {
            // Further: the BOM image does not yet have a DISTRO label...
            docker.withRegistry(DOCKER_REGISTRY, 'nexus') {
                scanner_image.inside(
                    "${mount_reference_repo_dir}" +
                    " -v ${checkout_dir}:${checkout_dir}" +
                    " --ulimit nofile=1024:1024" +
                    " --group-add=${docker_group_id}" +
                    " -v /var/run/docker.sock:/var/run/docker.sock"
                ) {
                    sh("""
                    python3 -m dependencyscanner \
                        --stage prod \
                        --outfile '${bom_path}' \
                        --research_file researched_master.yml \
                        --license_cache license_cache_master.json \
                        '${checkout_dir}'
                    """);
                }
            }
        }

        // remember: only one archiveArtifacts step per job allowed
        dir("${checkout_dir}") {
            show_duration("archiveArtifacts") {
                archiveArtifacts(
                    artifacts: relative_bom_path,
                    fingerprint: true,
                );
            }
        }

        stage("Upload BOM") {
            withCredentials([
                string(
                    credentialsId: 'dtrack',
                    variable: 'DTRACK_API_KEY')
            ]) {
                withEnv(["DTRACK_URL=${DTRACK_URL}"]) {
                    inside_container(
                        image: scanner_image,
                        args: [
                            "-v ${checkout_dir}:${checkout_dir}", // why?!
                            "--env DTRACK_URL,DTRACK_API_KEY",
                        ],
                    ) {
                        sh("""
                        scripts/upload-bom \
                            --bom-path '${bom_path}' \
                            --project-name 'Checkmk ${branch_version}' \
                            --project-version '${version}'
                        """);
                    }
                }
            }
        }
    }
}

return this;
