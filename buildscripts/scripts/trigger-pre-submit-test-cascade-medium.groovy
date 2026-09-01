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

// @NonCPS: runs outside Jenkins CPS so HttpURLConnection (non-Serializable) is safe to hold.
@NonCPS
Map gerritGetChange(Map args) {
    def conn = new URL("https://review.lan.tribe29.com/a/changes/${args.change_id}?o=LABELS").openConnection();
    conn.setRequestMethod("GET");
    conn.setRequestProperty("Authorization", args.auth_header);
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
            def blocked_submit_rule_result = submit_rules.values().any { it.action == "BLOCK" };
            if (blocked_submit_rule_result) {
                is_blocked = true;
                break;
            }
        }
    }
    return is_blocked;
}

// Our chain rebase above resets Gerrit's "Verified" label and retriggers
// the standard CV job, which runs in parallel with our own test cascade.
// "Verified" has three states:
// -1 (Fails) -> merge not possible, fail
// 0 (No score) -> CV not done, wait
// +1 (Verified) -> CV passed, merge when all have +1
String gerritVerifiedState(Map args) {
    def result = gerritGetChange(change_id: args.change_id, auth_header: args.auth_header);
    if (result.status < 200 || result.status >= 300) {
        error("Gerrit get-change failed (HTTP ${result.status}): ${result.body}");
    }
    // Strip Gitiles XSS protection prefix (5 bytes) before parsing.
    def change_info = new groovy.json.JsonSlurper().parseText(result.body.drop(5));
    def votes = (change_info.labels?.Verified?.all ?: []).collect { vote -> vote.value ?: 0 };
    def has_failure = votes.any { vote -> vote < 0 };
    def has_pass = votes.any { vote -> vote > 0 };
    if (has_failure) {
        return "FAILED";
    }
    return has_pass ? "PASSED" : "PENDING";
}

// Waits until "Verified" is no longer pending on every open (status NEW) change
void waitForChainVerified(Map args) {
    def pending = args.all_commits_in_chain.findAll { commit -> "${args.all_change_info.get(commit).status}" == "NEW" };
    def deadline = System.currentTimeMillis() + args.timeout_minutes * 60 * 1000;
    withGerritHttpCredentials {
        def auth_header = "Basic " + "${GERRIT_USER}:${GERRIT_PASSWORD}".bytes.encodeBase64().toString();
        while (true) {
            pending = pending.findAll { commit ->
                gerritVerifiedState(change_id: "${args.all_change_info.get(commit).id}", auth_header: auth_header) == "PENDING"
            };
            if (!pending) {
                break;
            }

            if (System.currentTimeMillis() >= deadline) {
                def pending_numbers = pending.collect { commit -> args.all_change_info.get(commit).number };
                error("Timed out after ${args.timeout_minutes}min waiting for Gerrit CV on change(s) ${pending_numbers}.");
            }

            sleep(args.poll_interval_seconds);
        }
    }
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

/// The package pre-build and the test jobs are the same call with the same
/// package identity, so keep it in one place: if the two drift apart, the test
/// jobs stop finding the pre-built package and build their own.
///
/// @extra_build_params: entries specific to one job, e.g. TEST_FILTER. They take
///     part in build matching, so a cached build from a run with different values
///     does not get reused.
/// @force_build: only where a cache hit is a problem, which is the package. The
///     test jobs are already distinct through their own parameters.
void triggerCascadeJob(Map args) {
    smart_build(
        // see global-defaults.yml, needs to run in minimal container
        use_upstream_build: true,
        force_build: args.force_build ?: false,
        relative_job_name: args.relative_job_name,
        build_params: [
            CUSTOM_GIT_REF: args.git_ref,
            EDITION: args.edition,
            DISTRO: args.distro,
            DISABLE_CACHE: args.disable_cache,
            DISABLE_CMK_DISTRO_PACKAGE_SIGNING: args.disable_signing,
            FAKE_ARTIFACTS: args.fake_artifacts,
        ] + (args.extra_build_params ?: [:]),
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

/// Build the TEST_FILTER of one cascade entry.
///
/// run_tests.sh evals TEST_FILTER as shell tokens, so it carries plain pytest
/// options as well as markers.
///
/// At most one marker belongs here: the make targets append their own "-m" after
/// TEST_FILTER and pytest lets the last one win. "-m medium_test_chain" also
/// switches test-system-singlesite-single.groovy to its marker-only target, so an
/// entry that wants the whole suite sharded must not carry it.
String composeTestFilter(Map args) {
    def parts = [];
    if (args.marker) {
        parts.add("-m ${args.marker}");
    }
    if (args.shard_count && args.shard_count > 1) {
        parts.add("--shard-index ${args.shard_index} --shard-count ${args.shard_count}");
    }
    parts.addAll(args.options ?: []);
    /// toString(), a GString reaching a build parameter is asking for trouble.
    return parts.join(" ").toString();
}

/// Name the finished build the shards take their runtimes from.
///
/// Returns "<job>#<number>". Every shard reads that build itself. Pinning the
/// number is what makes them agree: a finished test report never changes, so it
/// does not matter when a shard starts, and a reference job finishing midway
/// through the cascade changes nothing.
///
/// Raises when the report cannot be read or holds no test cases. The shards have
/// no fallback, so the job that fails should be this one, before eight pods have
/// built a site.
String resolveShardDurations(Map args) {
    def reference = "";
    /// Same credentials ci-artifacts is invoked with, see global-defaults.yml.
    withCredentials([usernamePassword(
        credentialsId: "jenkins-api-token",
        usernameVariable: "JENKINS_USERNAME",
        passwordVariable: "JENKINS_PASSWORD",
    )]) {
        reference = sh(
            returnStdout: true,
            script: ("${checkout_dir}/tests/scripts/resolve_shard_durations.py " +
                     "--job ${args.job}"),
        ).trim();
    }
    /// No second guard on the value: the script exits non-zero on any problem and
    /// prints nothing but the reference on stdout, its logging goes to stderr.
    println("Shards balance against ${reference}");
    return reference;
}

/// The entries of the medium cascade: stage label -> what to trigger for it.
///
/// Labels have to stay unique, the same job runs once per shard.
Map cascadeJobSpecs(Map args) {
    def specs = [:];
    /// The unsharded entry both suites use: the marked tests, nothing else.
    def marker_filter = composeTestFilter(marker: "medium_test_chain");
    def markerSpec = { job_name -> [
        job_name: job_name,
        build_params: [TEST_FILTER: marker_filter],
        start_delay: 0,
    ] };

    def multisite_job = "test-system-multisite-${args.edition}".toString();
    specs["${multisite_job} [marker]".toString()] = markerSpec(multisite_job);

    def singlesite_job = "test-system-singlesite-${args.edition}".toString();

    /// Sharding off: exactly what this cascade did before, one job on the marker.
    /// The switch is the SHARD_COUNT job parameter, so turning sharding on or off
    /// is a checkmk_ci change and needs no change here and no rebase of open chains.
    if (args.singlesite_shards < 2) {
        specs["${singlesite_job} [marker]".toString()] = markerSpec(singlesite_job);
        return specs;
    }

    /// The whole single site suite, split over N jobs. No marker here: the point
    /// is to run more than the marked tests, see composeTestFilter().
    (0..<args.singlesite_shards).each { shard ->
        def label = "${singlesite_job} [shard ${shard + 1}/${args.singlesite_shards}]";
        specs[label.toString()] = [
            job_name: singlesite_job,
            build_params: [
                TEST_FILTER: composeTestFilter(
                    shard_index: shard,
                    shard_count: args.singlesite_shards,
                    options: [args.medium_chain_option],
                ),
                /// A build parameter and not part of TEST_FILTER, so the job
                /// documents where its runtimes come from. It is matched, which
                /// is what stops a cached shard build from an earlier run with
                /// different runtimes being reused into this split.
                SHARD_BUILD_BASED_ON: args.shard_durations_build,
            ],
            start_delay: shard == 0 ? 0 : args.package_visibility_delay,
        ];
    }
    return specs;
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
    /// Run the whole single site suite instead of only the tests carrying the
    /// medium_test_chain marker, split over this many pods. Each shard builds its
    /// own site, so the cost is N site setups against roughly 1/N of the runtime.
    /// The split is computed in pytest, see tests/testlib/pytest_helpers/sharding.py.
    ///
    /// A job parameter so the number can be tuned from checkmk_ci without a change
    /// here. The fallback keeps this working before that parameter is deployed.
    ///
    /// One value for the whole cascade for now, since only the single site suite
    /// is sharded. Once multisite shards too it needs a value per suite, they do
    /// not want the same number.
    def singlesite_shards = (params.SHARD_COUNT ?: 8) as Integer;
    /// Build the shards take their runtimes from. Heavy has no singlesite job on
    /// the gate's edition, so this is the closest full report. Only used for
    /// balancing, never for selecting, so the mismatch does not matter.
    /// Full job path, so this works from the Testing folder and on any branch.
    def durations_job = "${branch_base_folder}/heavy/test-system-singlesite-ultimatemt";
    /// Tests that cannot work pre-submit carry "skip_if_medium_chain".
    def medium_chain_option = "--medium-chain";
    /// The pre-build below waits for the package, but every shard still does its
    /// own ci-artifacts lookup. Let the first go and hold the rest back briefly,
    /// so that lookup finds the pre-built package instead of racing for it.
    def package_visibility_delay = 60;
    def job_specs = [:];
    def new_patchset_revision = effective_git_ref;
    def medium_chain_hashtag = "medium-chain-running";
    def gerrit_project = "check_mk";
    def gerrit_verified_poll_interval_seconds = 30;
    def gerrit_verified_wait_timeout_minutes = 30;
    /// In order to ensure a fixed order for stages executed in parallel,
    /// we wait an increasing amount of time (N * 1s).
    /// Without this we end up with a capped build overview matrix in the job view (Jenkins doesn
    /// like changing order or amount of stages, which will happen with stages started `via paral
    def timeOffsetForOrder = 0;

    print(
        """
        |===== CONFIGURATION ===============================
        |branch_base_folder: │${branch_base_folder}│
        |cv_verified_min:... │${gerrit_verified_wait_timeout_minutes}│
        |disable_cache:..... │${disable_cache}│
        |disable_signing:... │${disable_signing}│
        |do_automerge:...... │${do_automerge}│
        |do_rebase:......... │${do_rebase}│
        |fake_artifacts:.... │${fake_artifacts} (always active)│
        |force_build:....... │${force_build}│
        |singlesite_shards:. │${singlesite_shards}│
        |durations_job:..... │${durations_job}│
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

            /// Before the package pre-build and fatal on purpose: an unusable
            /// reference should stop the cascade here, see resolveShardDurations().
            /// Skipped entirely while sharding is off, so the switch also takes the
            /// Jenkins API call out of the gate's path.
            smart_stage(
                name: "Resolve shard durations",
                raiseOnError: true,
            ) {
                job_specs = cascadeJobSpecs(
                    edition: edition_medium_chain,
                    singlesite_shards: singlesite_shards,
                    medium_chain_option: medium_chain_option,
                    package_visibility_delay: package_visibility_delay,
                    shard_durations_build: (singlesite_shards < 2) ? "" : resolveShardDurations(job: durations_job),
                );
                println("Cascade entries:");
                job_specs.each { label, spec ->
                    println("  ${label}: ${spec.build_params}");
                }
            }

            smart_stage(
                name: "Pre-build needed package",
                raiseOnError: true,
            ) {
                triggerCascadeJob(
                    relative_job_name: "${branch_base_folder}/builders/trigger-cmk-distro-package",
                    git_ref: new_patchset_revision,
                    edition: edition_medium_chain,
                    distro: distro_medium_chain,
                    disable_cache: force_build,
                    disable_signing: disable_signing,
                    fake_artifacts: fake_artifacts,
                    force_build: force_build,
                );
            }
        }

        def stages = job_specs.collectEntries { stage_label, spec ->
            [(stage_label) : {
                sleep(1 * timeOffsetForOrder++);
                if (spec.start_delay) {
                    println("Holding ${stage_label} for ${spec.start_delay}s so the pre-built " +
                            "package is visible to ci-artifacts before this shard asks for it");
                    sleep(spec.start_delay);
                }

                smart_stage(
                    name: "Trigger ${stage_label}",
                ) {
                    triggerCascadeJob(
                        relative_job_name: "${branch_base_folder}/cv/${spec.job_name}",
                        git_ref: new_patchset_revision,
                        edition: edition_medium_chain,
                        distro: distro_medium_chain,
                        disable_cache: force_build,
                        disable_signing: disable_signing,
                        fake_artifacts: fake_artifacts,
                        extra_build_params: spec.build_params,
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
                            // Skip the CV wait entirely if the branch is already closed - we are
                            // not going to submit anyway. We want to vote but not submit.
                            if (isBranchSubmitBlocked(gerrit_project, safe_branch_name)) {
                                voteGerrit(vote: 2, submit: false, identifier: new_patchset_revision);
                                println("NOT submitted: The branch is currently closed.");
                            } else {
                                // Our rebase reset Verified on every open change in the chain and
                                // retriggered CV; wait for it to resolve before attempting submit,
                                // rather than racing it (CMK-37686).
                                waitForChainVerified(
                                    all_commits_in_chain: all_commits_in_chain,
                                    all_change_info: all_change_info,
                                    poll_interval_seconds: gerrit_verified_poll_interval_seconds,
                                    timeout_minutes: gerrit_verified_wait_timeout_minutes,
                                );

                                // Check again right before submit: the branch could have closed
                                // while we were waiting for CV above (see isBranchSubmitBlocked).
                                if (isBranchSubmitBlocked(gerrit_project, safe_branch_name)) {
                                    voteGerrit(vote: 2, submit: false, identifier: new_patchset_revision);
                                    println("NOT submitted: The branch is currently closed.");
                                } else {
                                    voteGerrit(vote: 2, submit: true, identifier: new_patchset_revision);
                                }
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
