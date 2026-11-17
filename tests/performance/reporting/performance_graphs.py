#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""The graphs perftest_plot.py draws: runtime per scenario and job, and CPU and memory usage
over the course of each scenario."""

# mypy: disable-error-code="comparison-overlap"
# mypy: disable-error-code="no-any-return"
# mypy: disable-error-code="type-arg"

import logging
from collections.abc import Sequence
from datetime import datetime as Datetime
from pathlib import Path
from statistics import fmean

from matplotlib import colormaps, gridspec, pyplot

from tests.performance.reporting.performance_db import MeasurementsList, PerformanceData

logger = logging.getLogger(__name__)


class PerformanceGraphs:
    """Draws the graphs of loaded performance jobs into image files."""

    def __init__(
        self,
        jobs: PerformanceData,
        job_names: Sequence[str],
        scenario_names: Sequence[str],
        cpu_usage_metric: str,
        memory_usage_metric: str,
    ) -> None:
        self.jobs = jobs
        self.job_names = job_names
        self.scenario_names = scenario_names
        self.cpu_usage_metric = cpu_usage_metric
        self.memory_usage_metric = memory_usage_metric
        self.colormap = "tab10"

    @staticmethod
    def _px(val: int) -> int:
        """Return a figsize value given in pixels"""
        return 1 / pyplot.rcParams["figure.dpi"] * val

    def _plottable_benchmark_data(
        self, scenario_name: str
    ) -> tuple[list[float | None], list[float | None]]:
        """
        Extracts plottable mean and standard deviation values for a given benchmark scenario.

        Args:
            scenario_name (str): The name of the benchmark scenario to extract data for.

        Returns:
            tuple[list[int | float], list[int | float]]:
                - A list of mean values for the specified scenario across all jobs.
                - A list of standard deviation values for the specified scenario across all jobs.
                Note: If a job does not contain scenario data, None is appended for both values.
        """
        values: list[float | None] = []
        err_values: list[float | None] = []
        for _, benchmark_data in self.jobs.items():
            if not (
                isinstance(benchmark_data[0], dict)
                and isinstance(benchmark_data[0]["benchmarks"], list)
            ):
                continue
            if benchmark := next(
                (
                    _benchmark
                    for _benchmark in benchmark_data[0]["benchmarks"]
                    if isinstance(_benchmark, dict) and str(_benchmark["name"]) == scenario_name
                ),
                None,
            ):
                values.append(benchmark["stats"]["mean"])
                err_values.append(benchmark["stats"]["stddev"])
            else:
                values.append(None)
                err_values.append(None)
        return values, err_values

    def plot_benchmark_graph(self, graph_file: Path) -> None:
        """
        Generates and saves a benchmark graph for each scenario.

        For each scenario, this method retrieves benchmark values and error values, formats the
        labels, and plots an error bar graph showing execution times per job. The graph includes
        error bars, grid lines, and custom axis labels. The resulting plot is saved as an image
        file in the specified location.

        Args:
            graph_file (Path): The file path of the output graph image.

        Returns:
            None
        """
        # Define a color palette for better visual distinction
        colors = colormaps.get_cmap(self.colormap)(range(8))

        for scenario_name in self.scenario_names:
            raw_values, raw_err_values = self._plottable_benchmark_data(scenario_name)
            if not (raw_values and raw_err_values) or all(_ in (0, None) for _ in raw_values):
                continue
            graph_file_path = graph_file.parent / f"{scenario_name}.{graph_file.name}"
            logger.info('Writing graph "%s"...', graph_file_path)
            alternate = len(self.jobs) > 6
            max_value = 0
            values: list[float] = []
            err_values: list[float] = []
            names: list[str] = []
            for idx, benchmark in enumerate(self.jobs):
                value = raw_values[idx]
                err_value = raw_err_values[idx]
                if value is None or err_value is None:
                    continue
                max_value = int(max(value + err_value + 1, max_value))
                name = f"{benchmark}\n{round(value, 1)}s (+/-{round(err_value, 1)}s)"
                if alternate and idx % 2 == 1:
                    name = f"\n\n{name}"
                values.append(value)
                err_values.append(err_value)
                names.append(name)

            fig, times = pyplot.subplots(1, figsize=(self._px(1920), self._px(1080)))

            # Improve overall figure styling
            fig.suptitle(
                f"Benchmark: {scenario_name} (single execution)", fontsize=16, fontweight="bold"
            )
            fig.patch.set_facecolor("white")

            # Create error bar plot with improved styling
            times.errorbar(
                x=names,
                y=values,
                yerr=err_values,
                fmt="o",
                capsize=5,
                capthick=2,
                elinewidth=2,
                markersize=8,
                linewidth=2,
                color=colors[0],
                markerfacecolor=colors[1],
                markeredgecolor=colors[0],
                alpha=0.8,
            )

            # Improve axis styling
            times.set_ylim(ymin=0, ymax=max_value * 1.1)
            times.set_ylabel("Time (s)", fontsize=12)
            times.set_xlabel("Job", fontsize=12)
            times.set_yscale("linear")

            # Improve grid styling
            times.grid(True, which="major", axis="y", linestyle="-", alpha=0.3, linewidth=0.8)
            times.grid(True, which="minor", axis="y", linestyle=":", alpha=0.2, linewidth=0.5)
            times.set_yticks(ticks=range(0, max_value, max(1, max_value // 10)), minor=False)
            times.set_yticks(ticks=range(0, max_value, max(1, max_value // 20)), minor=True)

            # Style the axes and background
            times.set_facecolor("#f8f9fa")
            times.spines["top"].set_visible(False)
            times.spines["right"].set_visible(False)
            times.spines["left"].set_color("#cccccc")
            times.spines["bottom"].set_color("#cccccc")
            times.tick_params(axis="both", which="major", labelsize=10)
            times.tick_params(axis="x", rotation=0)

            # Add subtle data point annotations for better readability
            for i, (name, value, err) in enumerate(zip(names, values, err_values)):
                times.annotate(
                    f"{value:.1f}s",
                    (i, value + err + max_value * 0.02),
                    ha="center",
                    va="bottom",
                    fontsize=9,
                    alpha=0.7,
                    fontweight="bold",
                )

            # Save with high DPI for better quality
            pyplot.savefig(graph_file_path, dpi=300, facecolor="white", edgecolor="none")
            pyplot.close()

    @staticmethod
    def _plottable_resource_data(
        statistics: MeasurementsList, metric_name: str
    ) -> tuple[list[float], list[float]]:
        """
        Extracts and prepares resource usage data for plotting from a list of measurement values.

        Args:
            statistics (MeasurementsList): A list of measurement dictionaries containing timestamp
                and resource usage data.
            metric_name (str): The name used to identify the specific metric.

        Returns:
            tuple[list[float], list[float]]:
                - A list of durations (in seconds) between each timestamp, suitable for use as the
                  x-axis in a plot.
                - A list of resource usage measurements (as floats), suitable for use as the
                  y-axis in a plot.

        Notes:
            - Only statistics that are dictionaries and contain valid timestamp and resource usage
              values are processed.
            - The durations are calculated as evenly spaced intervals between the first and last
              timestamps.
            - Resource usage values are converted to floats for consistency.
        """

        def get_durations(timestamps: list[str]) -> list[float]:
            """
            Calculates evenly spaced durations between the first and last timestamps.

            Args:
                timestamps (list[str]): List of ISO format timestamp strings.

            Returns:
                list[float]: List of durations (in seconds) from the start time, evenly spaced
                    between the first and last timestamp.
            """
            start_time = Datetime.fromisoformat(timestamps[0])
            end_time = Datetime.fromisoformat(timestamps[-1])
            duration = end_time - start_time
            interval = round(duration.total_seconds() / len(timestamps), 1)
            return [i * interval for i in range(len(timestamps))]

        timestamps: list[str] = []
        measurements: list[float] = []
        for stats in statistics:
            if not isinstance(stats, dict):
                continue
            timestamp = str(stats["time"])
            raw_value = stats[metric_name]
            if isinstance(raw_value, int | float | str):
                value = float(raw_value)
                timestamps.append(timestamp)
                measurements.append(value)
        return get_durations(timestamps), measurements

    def plot_resource_graph(self, graph_file: Path, history: bool = False) -> None:
        """
        Plots resource usage graphs (CPU, memory) for each scenario and saves them as image files.

        For each scenario, this method creates a figure with two subplots:
        one for CPU usage and one for memory usage. It iterates over all selected jobs, extracts
        the relevant statistics, and plots the resource usage over time. The average usage is also
        plotted as a dashed line. Each plot is labeled with the job name and its average usage.

        The resulting graphs are saved to the specified `graph_file` location, with filenames
        including the scenario name.

        Args:
            graph_file (Path): The path to save the generated graph images.
            history (bool): A historical comparison graph is plotted.

        Returns:
            None
        """
        # Define a color palette for better visual distinction
        colors = colormaps.get_cmap(self.colormap)(range(len(self.jobs)))
        pyplot.subplots_adjust(hspace=100)
        for scenario_name in self.scenario_names:
            if scenario_name == "teardown_central_site":
                continue
            gs = gridspec.GridSpec(2, 1, height_ratios=[1, 1], hspace=0.3)
            fig = pyplot.figure(figsize=(self._px(1920), self._px(1080)))
            ax_cpu = fig.add_subplot(gs[0])
            ax_mem = fig.add_subplot(gs[1])

            # Improve overall figure styling
            graph_suffix = graph_file.name.removeprefix(scenario_name).removesuffix(
                f"resources{graph_file.suffix}"
            )
            subplot_title = f"{scenario_name}.{graph_suffix}".removesuffix(".")
            fig.suptitle(
                f"Resource usage: {subplot_title}",
                fontsize=16,
                fontweight="bold",
            )
            fig.set_size_inches(self._px(1920), self._px(1080))
            fig.set_linewidth(1.0)
            fig.patch.set_facecolor("white")

            graph_file_path = graph_file.parent / f"{scenario_name}.{graph_file.name}"
            logger.info('Writing graph "%s"...', graph_file_path)

            xmax = 60
            jobs = self.jobs if history else {self.job_names[-1]: self.jobs[self.job_names[-1]]}
            for job_idx, (job_name, data) in enumerate(jobs.items()):
                statistics = data[1].get(scenario_name, [])
                color = colors[job_idx % len(colors)]

                for subplot, metric_name, title in [
                    (ax_cpu, self.cpu_usage_metric, "CPU"),
                    (ax_mem, self.memory_usage_metric, "Virtual Memory"),
                ]:
                    if not statistics:
                        continue

                    durations, values = self._plottable_resource_data(statistics, metric_name)
                    xmax = int(durations[-1]) if durations and durations[-1] > xmax else xmax
                    average = fmean(values or [0])

                    # Plot main line with improved styling
                    subplot.plot(
                        durations,
                        values,
                        label=f"{job_name} (avg={round(average, 1)}%)",
                        alpha=0.8,
                        linewidth=1.0,
                        color=color,
                    )

                    # Draw average line with better styling
                    subplot.axhline(
                        y=average, linestyle="--", color=color, alpha=0.6, linewidth=1.5
                    )

                    # Improve subplot styling
                    subplot.set_title(title, fontsize=14, fontweight="bold", pad=20)
                    subplot.set_ylabel("Usage (%)", fontsize=12)
                    subplot.set_xlabel("Time (seconds)", fontsize=12)
                    subplot.set_ylim(0, 100)
                    subplot.set_xlim(0, xmax)

                    # Add grid for better readability
                    subplot.grid(True, alpha=0.3, linestyle="-", linewidth=0.5)
                    subplot.set_facecolor("#f8f9fa")

                    # Improve legend styling
                    legend = subplot.legend(
                        loc="upper right", frameon=True, fancybox=True, shadow=True, fontsize=10
                    )
                    legend.get_frame().set_facecolor("white")
                    legend.get_frame().set_alpha(0.9)

                    # Style the axes
                    subplot.tick_params(axis="both", which="major", labelsize=10)
                    subplot.spines["top"].set_visible(False)
                    subplot.spines["right"].set_visible(False)
                    subplot.spines["left"].set_color("#cccccc")
                    subplot.spines["bottom"].set_color("#cccccc")

            # Save with high DPI for better quality
            pyplot.savefig(
                graph_file_path,
                dpi=300,
                facecolor="white",
                edgecolor="none",
            )
            pyplot.close()
