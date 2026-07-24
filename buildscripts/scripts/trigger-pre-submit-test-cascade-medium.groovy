#!groovy

/// file: trigger-pre-submit-test-cascade-medium.groovy

// @NonCPS: runs outside Jenkins CPS so HttpURLConnection (non-Serializable) is safe to hold.
// Uses POST /a/changes/{id}/rebase:chain which rebases the full ancestor chain in one call
// (Gerrit 3.9+). Returns [status: int, body: String].
// on_behalf_of_uploader keeps the original patch owner as uploader/committer
@NonCPS
Map gerritRebaseChain(String patchset_revision, String auth_header) {
    def conn = new URL("https://review.lan.tribe29.com/a/changes/${patchset_revision}/rebase:chain?o=CURRENT_REVISION").openConnection();
    conn.setRequestMethod("POST");
    conn.setRequestProperty("Authorization", auth_header);
    conn.setRequestProperty("Content-Type", "application/json; charset=UTF-8");
    conn.setDoOutput(true);
    conn.outputStream.write('{"on_behalf_of_uploader": true}'.getBytes("UTF-8"));
    conn.outputStream.close();
    def http_status = conn.responseCode;
    def body = (http_status >= 200 && http_status < 300) ? conn.inputStream.text : (conn.errorStream?.text ?: "");
    return [status: http_status, body: body];
}

List getRelatedChanges(Map args) {
    def allChanges = [];

    allChanges = sh(returnStdout: true, script: """
        git log --format=%H "${args.patchset_revision}" ^origin/"${args.safe_branch_name}"
    """).trim().split("\n");

    return allChanges;
}

// @NonCPS: runs outside Jenkins CPS so HttpURLConnection (non-Serializable) is safe to hold.
// Hashtags have no SSH command, only POST /a/changes/{id}/hashtags. Returns [status: int, body: String].
@NonCPS
Map gerritSetHashtags(Map args) {
    def conn = new URL("https://review.lan.tribe29.com/a/changes/${args.patchset_revision}/hashtags").openConnection();
    conn.setRequestMethod("POST");
    conn.setRequestProperty("Authorization", args.auth_header);
    conn.setRequestProperty("Content-Type", "application/json; charset=UTF-8");
    conn.setDoOutput(true);
    def add_tags_json = args.add_tags.collect { "\"${it}\"" }.join(",");
    def remove_tags_json = args.remove_tags.collect { "\"${it}\"" }.join(",");
    conn.outputStream.write("""{"add": [${add_tags_json}], "remove": [${remove_tags_json}]}""".getBytes("UTF-8"));
    conn.outputStream.close();
    def http_status = conn.responseCode;
    def body = (http_status >= 200 && http_status < 300) ? conn.inputStream.text : (conn.errorStream?.text ?: "");
    return [status: http_status, body: body];
}

void setGerritHashtags(Map args) {
    withGerritHttpCredentials {
        def auth_header = "Basic " + "${GERRIT_USER}:${GERRIT_PASSWORD}".bytes.encodeBase64().toString();
        def result = gerritSetHashtags(
            patchset_revision: args.identifier,
            add_tags: args.add_tags,
            remove_tags: args.remove_tags,
            auth_header: auth_header,
        );
        if (result.status < 200 || result.status >= 300) {
            error("Gerrit set-hashtags failed (HTTP ${result.status}): ${result.body}");
        }
    }
}

// @NonCPS: runs outside Jenkins CPS so HttpURLConnection (non-Serializable) is safe to hold.
@NonCPS
Map gerritGetAccess(String project, String auth_header) {
    def conn = new URL("https://review.lan.tribe29.com/a/access/?project=${project}").openConnection();
    conn.setRequestMethod("GET");
    conn.setRequestProperty("Authorization", auth_header);
    def http_status = conn.responseCode;
    def body = (http_status >= 200 && http_status < 300) ? conn.inputStream.text : (conn.errorStream?.text ?: "");
    return [status: http_status, body: body];
}

// Matches Gerrit's three ref pattern styles: exact, wildcard (refs/heads/*), and regex (^refs/heads/.*).
// Mirrors refPatternMatches() in gerrit/plugins/ci-block-banner/.../ci_block_banner.js.
@NonCPS
Boolean refPatternMatches(String pattern, String target_ref) {
    if (pattern == target_ref) {
        return true;
    }
    if (pattern.endsWith("/*")) {
        return target_ref.startsWith(pattern[0..-2]);
    }
    if (pattern.startsWith("^")) {
        try {
            return java.util.regex.Pattern.compile(pattern).matcher(target_ref).find();
        } catch (e) {
            return false;
        }
    }
    return false;
}

// The sheriffing "close" action (see src/gerrit_management/manage_gerrit.py) adds a BLOCK
// rule on the "submit" permission for refs/heads/{branch}. This function detects that state.
Boolean isBranchSubmitBlocked(String project, String branch) {
    def is_blocked = false;
    withGerritHttpCredentials {
        def auth_header = "Basic " + "${GERRIT_USER}:${GERRIT_PASSWORD}".bytes.encodeBase64().toString();
        def result = gerritGetAccess(project, auth_header);
        if (result.status < 200 || result.status >= 300) {
            error("Gerrit get-access failed (HTTP ${result.status}): ${result.body}");
        }
        // Strip Gitiles XSS protection prefix (5 bytes) before parsing.
        def access_info = new groovy.json.JsonSlurper().parseText(result.body.drop(5));
        def target_ref = "refs/heads/${branch}";
        def local = access_info[project]?.local ?: [:];
        for (entry in local) {
            if (!refPatternMatches(entry.key, target_ref)) {
                continue;
            }
            def submit_rules = entry.value.permissions?.submit?.rules ?: [:];
            if (submit_rules.values().any { it.action == "BLOCK" }) {
                is_blocked = true;
                break;
            }
        }
    }
    return is_blocked;
}

// notify defaults to Gerrit's own default ("ALL") so callers only need to pass
// it for the intermediate/progress votes we want to keep quiet.
void voteGerrit(Map args) {
    def defaultDict = [
        label  : "medium-chain-verified",
        vote   : -1,
        submit : false,
        notify : "ALL",
    ] << args;
    def submit_flag = defaultDict.submit ? "--submit" : "";
    withGerritSshKey {
        sh("""
            ssh -i "\${GERRIT_SSH_KEY}" -o StrictHostKeyChecking=no \
                -p 29418 jenkins@review.lan.tribe29.com \
                gerrit review \
                --${defaultDict.label}=${defaultDict.vote} \
                --notify ${defaultDict.notify} \
                ${submit_flag} \
                ${defaultDict.identifier}
        """);
    }
}

// groovylint-disable MethodSize
void main() {
    def package_helper = load("${checkout_dir}/buildscripts/scripts/utils/package_helper.groovy");
    def versioning = load("${checkout_dir}/buildscripts/scripts/utils/versioning.groovy");

    /// This will get us the location to e.g. "checkmk/master" or "Testing/<name>/checkmk/master"
    def branch_base_folder = package_helper.branch_base_folder(true);
    def safe_branch_name = versioning.safe_branch_name();

    def disable_cache = params.DISABLE_CACHE;
    def do_rebase = params.CIPARAM_GATED_TRIGGER_REBASE;
    def do_automerge = params.CIPARAM_GATED_TRIGGER_AUTOMERGE;
    def disable_signing = params.DISABLE_CMK_DISTRO_PACKAGE_SIGNING;
    def fake_artifacts = true;
    def force_build = params.DISABLE_JENKINS_CACHE == true;

    def all_commits_in_chain = [];
    def all_change_info = [:];
    def edition_medium_chain = "ultimate";
    def distro_medium_chain = "ubuntu-24.04";
    def job_names = [
        "test-composition-${edition_medium_chain}",
        "test-integration-${edition_medium_chain}",
    ];
    def new_patchset_revision = effective_git_ref;
    def medium_chain_hashtag = "medium-chain-running";
    def gerrit_project = "check_mk";

    print(
        """
        |===== CONFIGURATION ===============================
        |branch_base_folder: │${branch_base_folder}│
        |disable_cache:..... │${disable_cache}│
        |disable_signing:... │${disable_signing}│
        |do_automerge:...... │${do_automerge}│
        |do_rebase:......... │${do_rebase}│
        |fake_artifacts:.... │${fake_artifacts} (always active)│
        |force_build:....... │${force_build}│
        |job_names:......... │${job_names}│
        |safe_branch_name:.. │${safe_branch_name}│
        |===================================================
        """.stripMargin());

    try {
        // This avoids the pods for the tests waiting for the package to be built.
        // The test pods are expensive and would only idle in that time.
        inside_container_minimal(safe_branch_name: safe_branch_name) {
            // silent-start is enabled on this trigger to prevent Verified=0 being cast
            // at build start. Post the build URL manually instead.
            if (new_patchset_revision) {
                withGerritSshKey {
                    sh("""
                        ssh -i "\${GERRIT_SSH_KEY}" -o StrictHostKeyChecking=no \
                            -p 29418 jenkins@review.lan.tribe29.com \
                            gerrit review \
                            --message "'Build started: ${env.BUILD_URL}'" \
                            --notify NONE \
                            ${new_patchset_revision}
                    """);

                    // pull changes, but do not yet rebase. Required to get all commits in the chain compared to base branch
                    dir("${checkout_dir}") {
                        withEnv(["GIT_SSH_COMMAND=ssh -o 'StrictHostKeyChecking no' -i ${GERRIT_SSH_KEY} -l jenkins"]) {
                            sh("""
                                git config --add user.name ${GERRIT_USER};
                                git config --add user.email ${JENKINS_MAIL};
                                time git fetch --no-tags --shallow-since=\$(date --date='2 weeks ago' --iso=seconds) origin \
                                    refs/heads/${safe_branch_name}:refs/remotes/origin/${safe_branch_name}
                            """);
                        }
                        all_commits_in_chain = getRelatedChanges([
                            safe_branch_name: safe_branch_name,
                            patchset_revision: new_patchset_revision,
                        ]);
                        println("Commits in chain: ${all_commits_in_chain}");
                    }
                }

                // Tag every change in the chain, not just the tip, so all of them show the running state.
                for (commit in all_commits_in_chain) {
                    setGerritHashtags(identifier: commit, add_tags: [medium_chain_hashtag], remove_tags: []);
                }
            }

            smart_stage(
                name: "Rebase chain on latest commit in Gerrit",
                condition: do_rebase,
                raiseOnError: true,
            ) {
                withGerritHttpCredentials {
                    // POST /a/changes/{id}/rebase:chain rebases the full ancestor chain in one
                    // server-side call. Response is a list of ChangeInfo (oldest→newest); the
                    // last entry is the tip change with its new current_revision.
                    def auth_header = "Basic " + "${GERRIT_USER}:${GERRIT_PASSWORD}".bytes.encodeBase64().toString();
                    def result = gerritRebaseChain(new_patchset_revision, auth_header);
                    if (result.status >= 200 && result.status < 300) {
                        // Strip Gitiles XSS protection prefix (5 bytes) before parsing.
                        // rebase:chain returns RebaseChainInfo {rebased_changes: [ChangeInfo...]}.
                        def rebase_info = new groovy.json.JsonSlurper().parseText(result.body.drop(5));
                        def rebased_revision = rebase_info.rebased_changes?.last()?.current_revision;
                        if (!rebased_revision) {
                            error("rebase:chain response missing rebased_changes or current_revision: ${result.body}");
                        }
                        new_patchset_revision = rebased_revision;
                    } else if (result.status == 409 && result.body.contains("already up to date")) {
                        println("Chain is already up to date, continuing with ${new_patchset_revision}");
                    } else {
                        error("Gerrit rebase failed (HTTP ${result.status}): ${result.body}");
                    }
                }
                println("New Patchset revision after Gerrit rebase: ${new_patchset_revision}");
            }

            smart_stage(
                name: "Pre-build needed package",
                raiseOnError: true,
            ) {
                smart_build(
                    // see global-defaults.yml, needs to run in minimal container
                    use_upstream_build: true,
                    force_build: force_build,
                    relative_job_name: "${branch_base_folder}/builders/trigger-cmk-distro-package",
                    build_params: [
                        CUSTOM_GIT_REF: new_patchset_revision,
                        EDITION: edition_medium_chain,
                        DISTRO: distro_medium_chain,
                        DISABLE_CACHE: force_build,
                        DISABLE_CMK_DISTRO_PACKAGE_SIGNING: disable_signing,
                        FAKE_ARTIFACTS: fake_artifacts,
                    ],
                    build_params_no_check: [
                        CIPARAM_OVERRIDE_BUILD_NODE: params.CIPARAM_OVERRIDE_BUILD_NODE,
                        CIPARAM_CLEANUP_WORKSPACE: params.CIPARAM_CLEANUP_WORKSPACE,
                        CIPARAM_BISECT_COMMENT: params.CIPARAM_BISECT_COMMENT,
                        CIPARAM_OVERRIDE_DOCKER_TAG_BUILD: params.CIPARAM_OVERRIDE_DOCKER_TAG_BUILD,
                    ],
                    no_remove_others: true, // do not delete other files in the dest dir
                    download: false,    // use copyArtifacts to avoid nested directories
                );
            }
        }

        def stages = job_names.collectEntries { job_name ->
            [("${job_name}") : {
                smart_stage(
                    name: "Trigger ${job_name}",
                ) {
                    smart_build(
                        // see global-defaults.yml, needs to run in minimal container
                        use_upstream_build: true,
                        force_build: force_build,
                        relative_job_name: "${branch_base_folder}/cv/${job_name}",
                        build_params: [
                            CUSTOM_GIT_REF: new_patchset_revision,
                            EDITION: edition_medium_chain,
                            DISTRO: distro_medium_chain,
                            DISABLE_CACHE: force_build,
                            DISABLE_CMK_DISTRO_PACKAGE_SIGNING: disable_signing,
                            FAKE_ARTIFACTS: fake_artifacts,
                            // if there is a test filter specified on make target level, the last one in the list of pytest arguments will
                            // overwrite all previous ones. Place all required test filters in one place and connect them with "and"
                            // "TEST_FILTER" is prepended to the pytest call and thereby always the first source of settings and so it is
                            // overruled if there is an additional test filter set later in the list of pytest args
                            // Remember to quote a chain of filters to prevent word splitting
                            // Setting "-m medium_test_chain" will cause special handling in "test-integration-single.groovy"
                            TEST_FILTER: '-m medium_test_chain',
                        ],
                        build_params_no_check: [
                            CIPARAM_OVERRIDE_BUILD_NODE: params.CIPARAM_OVERRIDE_BUILD_NODE,
                            CIPARAM_CLEANUP_WORKSPACE: params.CIPARAM_CLEANUP_WORKSPACE,
                            CIPARAM_BISECT_COMMENT: params.CIPARAM_BISECT_COMMENT,
                            CIPARAM_OVERRIDE_DOCKER_TAG_BUILD: params.CIPARAM_OVERRIDE_DOCKER_TAG_BUILD,
                        ],
                        no_remove_others: true, // do not delete other files in the dest dir
                        download: false,    // use copyArtifacts to avoid nested directories
                    );
                }
            }]
        }

        inside_container_minimal(safe_branch_name: safe_branch_name) {
            currentBuild.result = parallel(stages).values().every { it } ? "SUCCESS" : "FAILURE";
        }

        smart_stage(
            name: "Vote Medium-Chain-Verified and submit",
            condition: do_automerge, raiseOnError: false,
        ) {
            def success = currentBuild.result == "SUCCESS";
            if (success) {
                // On success, cast +1 on all (open) ancestor changes in the chain first.
                inside_container_minimal(safe_branch_name: safe_branch_name) {
                    withGerritSshKey {
                        for (commit in all_commits_in_chain) {
                            def commit_info = sh(returnStdout: true, script: """
                                ssh -i "\${GERRIT_SSH_KEY}" -o StrictHostKeyChecking=no \
                                    -p 29418 jenkins@review.lan.tribe29.com \
                                    gerrit query \
                                    --format=JSON --current-patch-set "commit:${commit}" \
                                    | head -n1 | jq -c '{id, number, subject, status, commit: .currentPatchSet.revision}'
                            """);
                            def changeInfo = new groovy.json.JsonSlurper().parseText(commit_info);
                            // [
                            //      commit:95d63af890e4ebddd596d56e1cbc910553a856c6,
                            //      id:Idfa88cd13d66c03c4bf87b04b9de46c0538e64a8,
                            //      number:143794,
                            //      status:NEW,
                            //      subject:Medium Chain: Granular Votes
                            // ]
                            println("changeInfo: ${changeInfo}");
                            all_change_info[commit] = changeInfo;

                            if ("${changeInfo.commit}" == "${new_patchset_revision}") {
                                println("Vote yourself +2");
                                voteGerrit(vote: 2, identifier: "${changeInfo.commit}", notify: "NONE");
                            } else {
                                // status can be: NEW, MERGED, ABANDONED. We want only new changes.
                                if ("${changeInfo.status}" == "NEW") {
                                    println("Vote ancestor ${changeInfo.number} aka ${changeInfo.id} +1");
                                    voteGerrit(vote: 1, identifier: "${changeInfo.commit}", notify: "NONE");
                                } else {
                                    println("No vote for ancestor ${changeInfo.number} aka ${changeInfo.id} as it is not 'NEW'");
                                }
                            }
                        }
                        println("all_change_info: ${all_change_info}");

                        // Try submit; if submit fails roll back all votes to 0.
                        try {
                            // Check right before submit: Gerrit's own submit rejection can't be
                            // relied on here (see isBranchSubmitBlocked)
                            // We want to vote but not submit.
                            if (isBranchSubmitBlocked(gerrit_project, safe_branch_name)) {
                                voteGerrit(vote: 2, submit: false, identifier: new_patchset_revision);
                                println("NOT submitted: The branch is currently closed.");
                            } else {
                                voteGerrit(vote: 2, submit: true, identifier: new_patchset_revision);
                            }
                        } catch (e) {
                            for (commit in all_commits_in_chain) {
                                def changeInfo = all_change_info.get(commit);
                                println("changeInfo: ${changeInfo}");

                                // status can be: NEW, MERGED, ABANDONED. We want only new changes.
                                if ("${changeInfo.status}" == "NEW") {
                                    println("Reset vote on ancestor ${changeInfo.number} aka ${changeInfo.id} to 0");
                                    voteGerrit(vote: 0, identifier: "${changeInfo.commit}", notify: "NONE");
                                }
                            }
                            // Unstable: ssh connection fails, exit code 255
                            // Failure:  rejected by Gerrit (conflict, unmet submit requirement)
                            //           any other error
                            if (!"${e.message}".contains("exit code 255")) {
                                currentBuild.result = "FAILURE";
                            }
                            throw e;
                        }
                    }
                }
            } else {
                voteGerrit(identifier: new_patchset_revision);
            }
        }
    } finally {
        // Runs regardless of success, failure, or an error() thrown above.
        // Caught so a failure here never masks the real build result.
        try {
            for (commit in all_commits_in_chain) {
                setGerritHashtags(identifier: commit, add_tags: [], remove_tags: [medium_chain_hashtag]);
            }
        } catch (e) {
            println("Failed to remove '${medium_chain_hashtag}' hashtag: ${e}");
        }
    }
}

return this;
