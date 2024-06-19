#!groovy

// file: build-announcement.groovy

// Builds a tar.gz which contains announcement text for publishing in the forum and on the mailing list.
// Artifacts will be consumed by bw-release.

def main() {
    stage("Clean workspace") {
        dir("${checkout_dir}") {
            // We don't want to fill up the workspace with old annoucement files
            sh(script: "make clean");
        }
    }
    stage("Build announcement") {
        inside_container() {
            dir("${checkout_dir}") {
                def announce_file = sh(script: 'make print-CHECK_MK_ANNOUNCE_TAR_FILE', returnStdout: true).trim();
                sh(script: "make announcement");
                show_duration("archiveArtifacts") {
                    archiveArtifacts(
                        artifacts: announce_file,
                        fingerprint: true,
                    );
                }
            }
        }
    }
}

return this;
