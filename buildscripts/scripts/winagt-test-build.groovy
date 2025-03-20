#!groovy

/// file: winagt-test-build.groovy

def main() {
    def windows = load("${checkout_dir}/buildscripts/scripts/utils/windows.groovy");
    def versioning = load("${checkout_dir}/buildscripts/scripts/utils/versioning.groovy");

    def safe_branch_name = versioning.safe_branch_name();
    def cmk_version = versioning.get_cmk_version(safe_branch_name, "daily");

    dir("${checkout_dir}") {
        stage("make setversion") {
            bat("make -C agents\\wnx NEW_VERSION='${cmk_version}' setversion");
        }
        windows.build(
            TARGET: "agent_no_sign"
        );
    }
}

return this;
