#!groovy

// file: build-announcement.groovy

// Builds a tar.gz which contains announcement text for publishing in the forum and on the mailing list.
// Artifacts will be consumed by bw-release.


def main() {
    stage("Build announcement") {
        docker_image_from_alias("IMAGE_TESTING").inside() {
            dir("${checkout_dir}") {

                def checkmk_version = sh(script: 'make print-VERSION', returnStdout: true).trim();
                print(
                    """
                |===== CONFIGURATION ===============================
                |checkmk_version:.......... |${checkmk_version}|
                |===================================================
                """.stripMargin()
                );
                ARTIFACT_NAME = "announce-" + checkmk_version + ".tar.gz"
                sh(script: "make `pwd`/${ARTIFACT_NAME}")
            }
    }

    stage("Archive artifacts") {
        dir("${checkout_dir}") {
            archiveArtifacts(
                artifacts: ARTIFACT_NAME,
                fingerprint: true,
                );
            }
        }
    }
}

return this;
