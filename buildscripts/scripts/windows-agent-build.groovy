#!groovy

def main() {
    check_job_parameters(["VERSION"]);
    
    def windows = load("${checkout_dir}/buildscripts/scripts/utils/windows.groovy");
    def versioning = load("${checkout_dir}/buildscripts/scripts/utils/versioning.groovy");
    
    def branch_name = versioning.safe_branch_name(scm);
    def cmk_version = versioning.get_cmk_version(branch_name, VERSION);

    dir("${checkout_dir}") {
        stage("make setversion") {
            bat("make -C agents\\wnx NEW_VERSION='${cmk_version}' setversion")
        }

        withCredentials([
            usernamePassword(
                credentialsId: 'win_sign',
                passwordVariable: 'WIN_SIGN_PASSWORD',
                usernameVariable: '')]) {
            windows.build(
                TARGET: 'agent_with_sign',
                PASSWORD: WIN_SIGN_PASSWORD,
            )
        }
    }
}
return this;

