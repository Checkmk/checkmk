#!groovy

/// file: build-cmk-bom.groovy

void main() {
    check_job_parameters([
        ["VERSION", true],
        ["EDITION", true],
    ]);

    def versioning = load("${checkout_dir}/buildscripts/scripts/utils/versioning.groovy");

    def version = params.VERSION;
    def edition = params.EDITION;

    def branch_version = versioning.get_branch_version(checkout_dir);
    def safe_branch_name = versioning.safe_branch_name();
    def cmk_version_rc_aware = versioning.get_cmk_version(safe_branch_name, branch_version, version);
    def cmk_version = versioning.strip_rc_number_from_version(cmk_version_rc_aware);

    /// Get the ID of the docker group from the node(!). This must not be
    /// executed inside the container (as long as the IDs are different)
    def docker_group_id = get_docker_group_id();

    print(
        """
        |===== CONFIGURATION ===============================
        |cmk_version:.............. │${cmk_version}│
        |cmk_version_rc_aware:..... │${cmk_version_rc_aware}│
        |edition:.................. │${edition}│
        |branch_version:........... │${branch_version}│
        |docker_group_id:.......... │${docker_group_id}│
        |===================================================
        """.stripMargin());

    stage("Make repo edition aware") {
        inside_container() {
            dir("${checkout_dir}") {
                versioning.configure_checkout_folder(edition, cmk_version);
            }
        }
    }

    dir("${checkout_dir}") {
        stage("Create bill-of-materials.csv") {
            inside_container() {
                sh("""
                    bazel build //omd/dependency_management:bill_of_materials_renamed
                    cp bazel-bin/omd/dependency_management/bill-of-materials.json omd/
                """);
            }
        }
        stage("Create bill-of-materials.csv") {
            inside_container() {
                sh("""
                    bazel build //omd/dependency_management:generate_bom_csv
                    cp bazel-bin/omd/dependency_management/bill-of-materials.csv omd/
                """);
            }
        }
    }

    // remember: only one archiveArtifacts step per job allowed
    dir("${checkout_dir}") {
        show_duration("archiveArtifacts") {
            archiveArtifacts(
                artifacts: "omd/bill-of-materials.json, omd/bill-of-materials.csv",
                fingerprint: true,
            );
        }
    }
}

return this;
