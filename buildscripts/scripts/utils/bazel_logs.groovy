#!groovy

/// file: bazel_logs.groovy

def try_parse_bazel_execution_log(distro, distro_dir, bazel_log_prefix) {
    try {
        dir("${distro_dir}") {
            def summary_file="${distro_dir}/${bazel_log_prefix}execution_summary_${distro}.json";
            def cache_hits_file="${distro_dir}/${bazel_log_prefix}cache_hits_${distro}.csv";
            sh("""python3 \
                buildscripts/scripts/bazel_execution_log_parser.py \
                --execution_logs_root "${distro_dir}" \
                --bazel_log_file_pattern "bazel_execution_log*" \
                --summary_file "${summary_file}" \
                --cachehit_csv "${cache_hits_file}" \
                --distro "${distro}"
            """);
            stash(name: "${bazel_log_prefix}${distro}", includes: "${bazel_log_prefix}*");

            // remove large execution log summary file to save some space, approx 1.6GB per workspace
            sh("rm -rf ${distro_dir}/${bazel_log_prefix}*.json");
        }
    } catch (e) {
        print("Failed to parse bazel execution logs: ${e}");
    }
}

def try_plot_cache_hits(bazel_log_prefix, distros) {
    try {
        distros.each { distro ->
            try {
                print("Unstashing for distro ${distro}...");
                unstash(name: "${bazel_log_prefix}${distro}");
            }
            catch (e) {
                print("No stash for ${distro}");
            }
        }

        plot(
            csvFileName: 'bazel_cache_hits.csv',
            csvSeries:
                distros.collect {[file: "${bazel_log_prefix}cache_hits_${it}.csv"]},
            description: 'Bazel Remote Cache Analysis',
            group: 'Bazel Cache',
            numBuilds: '30',
            propertiesSeries: [[file: '', label: '']],
            style: 'line',
            title: 'Cache hits',
            yaxis: 'Cache hits in percent',
            yaxisMaximum: '100',
            yaxisMinimum: '0'
        );

        archiveArtifacts(
           artifacts: "${bazel_log_prefix}*",
        )
    }
    catch (e) {
        print("Failed to plot cache hits: ${e}");
    }
}

return this;
