#!groovy

/// file: bazel_logs.groovy

def try_parse_bazel_execution_log(distro, distro_dir, bazel_log_prefix) {
    try {
        dir("${distro_dir}") {
            def summary_file="${distro_dir}/${bazel_log_prefix}execution_summary_${distro}.json";
            def cache_hits_file="${distro_dir}/${bazel_log_prefix}cache_hits_${distro}.csv";
            sh("""bash \
                buildscripts/scripts/bazel_execution_log_parser.sh \
                --execution_logs_root "${distro_dir}" \
                --bazel_log_file_pattern "deps_install.json" \
                --summary_file "${summary_file}" \
                --cachehit_csv "${cache_hits_file}" \
                --distro "${distro}"
            """);

            // remove large execution log summary file to save some space, approx ~900MB per workspace
            sh("rm -rf ${distro_dir}/deps_install.json");
        }
    } catch (e) {
        print("Failed to parse bazel execution logs: ${e}");
    }
}

def try_plot_cache_hits(bazel_log_prefix, distros) {
    try {
        plot(
            csvFileName: 'bazel_cache_hits.csv',
            csvSeries:
                distros.collect {[file: "${bazel_log_prefix}cache_hits_${it}.csv"]},
            description: 'Bazel Remote Cache Analysis',
            group: 'Bazel Cache',
            numBuilds: '30',
            style: 'line',
            title: 'Cache hits',
            yaxis: 'Cache hits in percent',
            yaxisMaximum: '100',
            yaxisMinimum: '0'
        );
    }
    catch (e) {
        print("Failed to plot cache hits: ${e}");
    }
}

return this;
