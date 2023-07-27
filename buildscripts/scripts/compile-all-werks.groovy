#!groovy

/// file: compile-all-werks.groovy
def provide_clone(repo_name, credentials_id) {
    dir("${WORKSPACE}/${repo_name}") {
        checkout([$class: "GitSCM",
            userRemoteConfigs: [[
                credentialsId: credentials_id,
                url: "ssh://jenkins@review.lan.tribe29.com:29418/${repo_name}",
                // refspec: "${refspec}",
            ]],
            // branches: [new hudson.plugins.git.BranchSpec(branches_str)],
            extensions: [
                [$class: 'CloneOption',
                    // reference: "${reference_clone}",
                    timeout: 20,
            ]],
        ]);
    }
}

def main() {
    stage("Checkout repositories") {
        provide_clone("cma", "ssh-git-gerrit-jenkins");
        provide_clone("checkmk_kube_agent", "ssh-git-gerrit-jenkins");
    }
    stage("Compile werks") {
        docker.withRegistry(DOCKER_REGISTRY, 'nexus') {
            docker_image_from_alias("IMAGE_TESTING").inside() {
                dir("${checkout_dir}") {
                    sh("""
                    scripts/run-pipenv run echo build venv..
                    scripts/run-pipenv run python3 -m cmk.utils.werks collect cmk ./cmk > cmk.json
                    scripts/run-pipenv run python3 -m cmk.utils.werks collect cma ${WORKSPACE}/cma > cma.json
                    scripts/run-pipenv run python3 -m cmk.utils.werks collect checkmk_kube_agent ${WORKSPACE}/checkmk_kube_agent > kube.json

                    # jq -s '.[0] * .[1] * .[2]' cma.json cmk.json kube.json > all_werks.json
                    # no need to install jq!!!!!
                    python3 -c 'import json, sys; print(json.dumps({k: v for f in sys.argv[1:] for k, v in json.load(open(f)).items() }, ident=4))' \
                        cmk.json \
                        cma.json \
                        kube.json \
                        > ${WORKSPACE}/all_werks.json
                    """);
                }
            }
        }
    }
    stage("Archive") {
        archiveArtifacts(
            artifacts: "${WORKSPACE}/all_werks.json",
            fingerprint: true,
        )
    }
}
return this;

