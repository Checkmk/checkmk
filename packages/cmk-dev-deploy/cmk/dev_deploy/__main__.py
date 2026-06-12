# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""Entry point for ``python3 -m cmk.dev_deploy``."""

from __future__ import annotations

import argparse
import atexit
import os
import sys
import termios
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from cmk.dev_deploy.frontend.frontend_supervisor import FrontendSupervisor
    from cmk.dev_deploy.types import FrontendConfig

from cmk.dev_deploy.cli import parse_args
from cmk.dev_deploy.core import output
from cmk.dev_deploy.deployers.bazel_builder import build_and_install
from cmk.dev_deploy.deployers.config_deployer import deploy_config
from cmk.dev_deploy.deployers.wheel_deployer import deploy_wheels, has_wheel_changes
from cmk.dev_deploy.errors import (
    ChangeDetectionError,
    DeployError,
    ManifestBuildError,
    RepoNotFoundError,
    SiteError,
    SiteNotFoundError,
    SudoersError,
)
from cmk.dev_deploy.execution.bazel_resolver import resolve_bazel_targets
from cmk.dev_deploy.execution.parallel import DeployStep, execute_parallel
from cmk.dev_deploy.execution.service_manager import resolve_services, restart_services
from cmk.dev_deploy.execution.source_paths import resolve_source_paths
from cmk.dev_deploy.execution.step_registry import (
    DEPLOYER_DISPLAY_NAMES,
    STEP_DISPLAY_NAMES,
    STEP_TO_DEPLOYER,
)
from cmk.dev_deploy.manifest.registry import uncovered_changed_files
from cmk.dev_deploy.site.privilege import SSHState
from cmk.dev_deploy.site.site_resolver import find_repo_root, resolve_site
from cmk.dev_deploy.site.warnings import check_branch_mismatch, check_edition_mismatch
from cmk.dev_deploy.state.change_detector import (
    detect_changes,
    filter_stale_dirty,
    has_reverted_dirty_files,
    state_has_dirty_files,
)
from cmk.dev_deploy.state.deploy_state import (
    build_and_save_state,
    compute_dirty_hashes,
    compute_file_hash,
    delete_state,
    DeployState,
    get_current_branch,
    get_head_commit,
    load_state,
    state_file_path,
)
from cmk.dev_deploy.state.path_skip import check_skip
from cmk.dev_deploy.types import (
    BazelTargetSet,
    ChangeCategory,
    ChangeSet,
    DeployCycleResult,
    SiteInfo,
    SkipResult,
    StepResult,
)
from cmk.dev_deploy.watcher import watch_loop


def _has_config_data_changes(changes: ChangeSet | None) -> bool:
    if changes is None:
        return True
    return ChangeCategory.CONFIG in changes.categories or ChangeCategory.DATA in changes.categories


def _compute_skip_results(
    args: argparse.Namespace,
    state: DeployState | None,
    repo_root: Path,
    site: SiteInfo,
) -> dict[str, SkipResult]:
    """Run per-deployer path-aware skip checks."""
    skip_results: dict[str, SkipResult] = {}
    if state is not None and not args.full:
        head = get_head_commit(repo_root)
        for deployer_name in ("config_spec", "install_spec"):
            result = check_skip(deployer_name, repo_root, site.root, state, head)
            skip_results[deployer_name] = result
            if result.paths_checked == () and not result.should_skip:
                if "HEAD fallback" in result.reason:
                    output.print_fallback_note(DEPLOYER_DISPLAY_NAMES[deployer_name])
    return skip_results


def _maybe_print_frontend_hint(changes: ChangeSet, frontend_supervised: bool) -> None:
    if not frontend_supervised:
        output.print_frontend_hint(changes)


def _warn_uncovered_files(
    state: DeployState | None,
    changes: ChangeSet | None,
    repo_root: Path,
) -> dict[str, str]:
    """Warn about changed files no deploy spec covers; the warning persists.

    Newly detected uncovered files are recorded (path -> content hash) in
    the deploy state, because the diff base advances past them after the
    cycle.  A recorded file keeps warning on every run until it is
    reverted or edited again (normal change detection then re-evaluates
    it) or a deploy spec starts covering it.  Files we know are never
    deployed (TEST/BUILD/IGNORED) are exempt; OTHER means "no rule
    matched", exactly where the registry coverage check is informative.
    """
    fresh: list[str] = []
    if changes is not None and not changes.is_empty:
        non_deploy_files: set[str] = set()
        for cat in (
            ChangeCategory.TEST,
            ChangeCategory.BUILD,
            ChangeCategory.IGNORED,
        ):
            non_deploy_files.update(changes.categories.get(cat, ()))
        deployable = tuple(f for f in changes.files if f not in non_deploy_files)
        fresh = uncovered_changed_files(deployable)

    uncovered: dict[str, str] = {}
    candidates = {
        path: recorded_hash
        for path, recorded_hash in (state.uncovered_files if state else {}).items()
        if path not in fresh  # re-recorded below with the current hash
        and (repo_root / path).is_file()
        and compute_file_hash(repo_root / path) == recorded_hash
    }
    # One batched registry check for all recorded entries
    for path in uncovered_changed_files(tuple(candidates)):
        uncovered[path] = candidates[path]
    for path in fresh:
        abs_path = repo_root / path
        if abs_path.is_file():
            uncovered[path] = compute_file_hash(abs_path)

    if uncovered:
        output.warn(
            f"{len(uncovered)} changed file(s) not covered by any deploy spec:\n"
            + "".join(f"  {f}\n" for f in sorted(uncovered))
            + "These changes will NOT be deployed."
        )
    return uncovered


def _print_timing_display(
    results: list[StepResult],
    total_elapsed: float,
    manifest_elapsed: float = 0.0,
    overlay_elapsed: float = 0.0,
    services_elapsed: float = 0.0,
) -> None:
    """Print total deploy time and optional verbose timing breakdown."""
    output.print_deploy_total(total_elapsed)
    if output.get_verbosity() >= output.Verbosity.VERBOSE:
        output.print_parallel_timeline(
            results,
            total_elapsed,
            manifest_elapsed,
            overlay_elapsed,
            services_elapsed,
        )


def _run_deploy_cycle(
    args: argparse.Namespace,
    repo_root: Path,
    site: SiteInfo,
    ssh_state: SSHState,
    manifest_elapsed: float = 0.0,
    overlay_elapsed: float = 0.0,
) -> DeployCycleResult:
    """Execute one deploy cycle: change detection through parallel execution."""
    import time as _time

    from cmk.dev_deploy.manifest.staleness import ensure_manifest

    _cycle_start = _time.monotonic()

    # Check manifest freshness on every cycle so that BUILD file edits
    # during watch sessions trigger a rebuild (not just at startup).
    ensure_manifest(repo_root)

    # Derive frontend_supervised from CLI args
    frontend_supervised = args.frontend

    # Track deployed/skipped deployer display names for cycle summary
    deployed_names: list[str] = []
    skipped_names: list[str] = []
    skipped_reasons: dict[str, str] = {}

    def _make_result(
        exit_code: int,
        *,
        all_skipped: bool = False,
        services_restarted: int = 0,
    ) -> DeployCycleResult:
        return DeployCycleResult(
            exit_code=exit_code,
            deployed=tuple(deployed_names),
            skipped=tuple(skipped_names),
            skipped_reasons=dict(skipped_reasons),
            services_restarted=services_restarted,
            all_skipped=all_skipped,
        )

    # --full handling: delete state before any deploy logic
    if args.full:
        delete_state(site.root)
        output.info("Full deploy: incremental state cleared")

    # Load existing state
    state = load_state(site.root)
    # If state file exists on disk but load returned None, it was corrupt
    if state is None and state_file_path(site.root).is_file():
        output.warn("Deploy state file is invalid, falling back to full deploy")

    # Branch switch detection
    current_branch = get_current_branch(repo_root)
    if state is not None and state.branch and current_branch and state.branch != current_branch:
        output.warn(
            f"Branch changed: {state.branch} -> {current_branch}. "
            "Clearing state and performing full deploy."
        )
        delete_state(site.root)
        state = None

    # Determine diff base: state commit > site build commit
    diff_base: str | None
    if state is not None and state.diff_base_commit:
        # Global diff base: always set to HEAD after each deploy cycle,
        # independent of per-deployer commits (which may be stale when
        # a deployer is repeatedly skipped).
        diff_base = state.diff_base_commit
    elif state is not None and state.deployers:
        # Fallback for schema v2 states without diff_base_commit:
        # use the most recently deployed commit across all deployers.
        latest = max(state.deployers.values(), key=lambda ds: ds.deployed_at)
        diff_base = latest.git_commit
    else:
        diff_base = site.build_commit

    if diff_base is not None:
        if state is not None and state.diff_base_commit:
            _source = "state"
        elif state is not None and state.deployers:
            _source = "state"
        else:
            _source = "site_build"
        output.print_state_info(_source, diff_base)

    # Change detection
    if output.get_verbosity() >= output.Verbosity.VERBOSE:
        output.print_blank()
    target_commit = args.commit
    changes = detect_changes(diff_base, repo_root, target_commit=target_commit)

    # Coverage warning (persists across runs via the deploy state); also
    # fires on cycles that end in an early "nothing to deploy" return.
    uncovered_files = _warn_uncovered_files(state, changes, repo_root)

    if changes is None:
        output.warn(
            "Site has no build commit (COMMIT file missing).\n"
            "Deploying all files without change detection."
        )
    elif changes.is_empty and not state_has_dirty_files(state):
        output.success("Nothing to deploy -- working tree matches site build.")
        return _make_result(0, all_skipped=True)
    elif changes.is_empty:
        # Working tree is clean, but a previous deploy cycle deployed dirty
        # files that have since been reverted.  Treat as a full deploy so
        # the per-deployer skip logic (which compares dirty_file_hashes)
        # can redeploy the now-clean files.
        output.info("Dirty files reverted -- redeploying clean state.")
        changes = None
    else:
        # Filter out dirty files that were already deployed with the same
        # content.  These appear in git diff every run but are not new work.
        if state is not None and state.deployers:
            changes = filter_stale_dirty(changes, state, repo_root)
            if changes.is_empty:
                # All remaining changes were stale dirty files.  But check
                # whether any previously-dirty files were reverted -- those
                # need the clean version redeployed.
                if has_reverted_dirty_files(state, repo_root):
                    output.info("Dirty files reverted -- redeploying clean state.")
                    changes = None  # full deploy to restore clean versions
                else:
                    output.success("Nothing to deploy -- dirty files unchanged since last deploy.")
                    return _make_result(0, all_skipped=True)

        if changes is not None:
            output.print_change_summary(changes)
            output.print_verbose_changes(changes, frontend_supervised=frontend_supervised)
            # Hint about --frontend when Vue files changed (noop when no VUE
            # files or when frontend_supervised is already active)
            _maybe_print_frontend_hint(changes, frontend_supervised)

    # Edition mismatch warning
    edition_warning = check_edition_mismatch(changes, site)
    if edition_warning:
        output.warn(edition_warning)

    # Bazel target resolution
    targets: BazelTargetSet | None = None
    if changes is not None and not changes.has_python_only:
        if output.get_verbosity() >= output.Verbosity.VERBOSE:
            output.print_blank()
        resolved = resolve_bazel_targets(
            changes, repo_root, frontend_supervised=frontend_supervised
        )
        # In watch mode, suppress //... (global rebuild) targets to avoid
        # 10+ minute full builds on every save during BUILD file editing.
        # Package-specific targets still build normally.
        if args.watch and any(t.label == "//..." for t in resolved.targets):
            filtered = tuple(t for t in resolved.targets if t.label != "//...")
            output.warn(
                "Global build files changed (MODULE.bazel or bazel/). "
                "Skipping full Bazel rebuild in watch mode.\n"
                "  Run a one-shot deploy when done: cdd"
            )
            if filtered:
                targets = BazelTargetSet(
                    targets=filtered,
                    files_queried=resolved.files_queried,
                    files_resolved=resolved.files_resolved,
                    from_cache=resolved.from_cache,
                    query_time_ms=resolved.query_time_ms,
                )
        else:
            targets = resolved
        if targets is not None:
            output.print_target_summary(targets)

    # Determine build path
    if changes is None:
        # No build commit -- deploy everything (existing behavior)
        build_path = "full"
    elif changes.has_python_only:
        build_path = "fast"
    elif targets is not None and targets.is_empty:
        # Non-Python files changed but no Bazel targets affected
        # (e.g., only config/data files). Still use fast path for any Python.
        build_path = "fast"
    else:
        build_path = "full"

    output.print_build_path(build_path)

    skip_results = _compute_skip_results(args, state, repo_root, site)

    # Dry-run short-circuit
    if args.dry_run:
        output.print_dry_run_plan(
            build_path=build_path,
            changes=changes,
            targets=targets,
            services=resolve_services(changes, targets, site),
        )
        return _make_result(0)

    # Verbose flag determines Bazel progress passthrough (default for TTY)
    verbose_build = args.verbose or sys.stdout.isatty()

    # Build deployment step list (unified for both fast and full paths)
    steps: list[DeployStep] = []
    deploy_step_names: list[str] = []

    # Config deploy: included if config/data changes detected (and not skipped)
    if _has_config_data_changes(changes):
        _cfg_result = skip_results.get("config_spec")
        if _cfg_result is not None and _cfg_result.should_skip:
            output.print_deployer_skipped_line(
                DEPLOYER_DISPLAY_NAMES["config_spec"], _cfg_result.reason
            )
            skipped_names.append("config")
            skipped_reasons["config"] = _cfg_result.reason
        else:

            def _config_action() -> str | None:
                config_result = deploy_config(changes, repo_root, site)
                if config_result.specs_deployed > 0:
                    msg = (
                        f"Config deployment complete in {config_result.elapsed:.1f}s"
                        f" ({config_result.specs_deployed} spec(s))"
                    )
                    output.print_deployer_deployed("config", config_result.elapsed, msg)
                    return msg
                return None

            steps.append(DeployStep(name="config_deploy", action=_config_action))
            deploy_step_names.append("config_deploy")

    # Bazel build: included only in full path when targets exist (and not skipped)
    if build_path == "full" and targets and not targets.is_empty:
        _bzl_result = skip_results.get("install_spec")
        if _bzl_result is not None and _bzl_result.should_skip:
            output.print_deployer_skipped_line(
                DEPLOYER_DISPLAY_NAMES["install_spec"], _bzl_result.reason
            )
            skipped_names.append("bazel")
            skipped_reasons["bazel"] = _bzl_result.reason
        else:
            _targets = targets  # capture for closure

            def _bazel_action() -> str | None:
                build_result = build_and_install(
                    _targets,
                    site,
                    repo_root,
                    verbose=verbose_build,
                    frontend_supervised=frontend_supervised,
                )
                msg = (
                    f"Bazel build complete in {build_result.elapsed:.1f}s"
                    f" ({build_result.targets_built} target(s),"
                    f" {build_result.artifacts_installed} artifact(s))"
                )
                output.print_deployer_deployed("bazel", build_result.elapsed, msg)
                return msg

            steps.append(DeployStep(name="bazel_build", action=_bazel_action))
            deploy_step_names.append("bazel_build")

    # Wheel deploy: included if any changed file belongs to a deployed wheel.
    # Bazel's action cache and uv's reinstall speed make per-package
    # selection unnecessary -- the step always reinstalls all wheels.
    if has_wheel_changes(changes):

        def _wheel_action() -> str | None:
            wheel_result = deploy_wheels(repo_root, site)
            msg = (
                f"Wheel deployment complete in {wheel_result.elapsed:.1f}s"
                f" ({wheel_result.wheels_installed} wheel(s) reinstalled)"
            )
            output.print_deployer_deployed("wheels", wheel_result.elapsed, msg)
            return msg

        steps.append(DeployStep(name="wheel_deploy", action=_wheel_action))
        deploy_step_names.append("wheel_deploy")

    # All deployers skipped -- nothing to execute
    if not deploy_step_names:
        output.print_all_skipped()
        # Still advance the global diff base so change detection doesn't
        # keep showing the same files on every run.
        build_and_save_state(
            repo_root,
            site.root,
            current_branch,
            successful_deployers=set(),
            previous_state=state,
            backend=args.backend or "",
            uncovered_files=uncovered_files,
        )
        return _make_result(0, all_skipped=True)

    # Execute parallel deployment (deploy steps only, services handled after)
    # Output buffering in parallel.py captures each step's output and flushes
    # it as contiguous blocks per-wave, so per-deployer summary lines emitted
    # inside action closures appear without interleaving.
    if output.get_verbosity() >= output.Verbosity.VERBOSE:
        output.print_blank()
        output.info(f"Deploying ({len(steps)} step(s), max {args.jobs} worker(s))...")
    # Snapshot per-deployer dirty-file hashes BEFORE deploying: a file
    # edited while the deploy runs must compare as changed on the next
    # cycle instead of being recorded as already deployed.
    _deployer_dirty: dict[str, dict[str, str]] = {}
    for dep_name in ("config_spec", "install_spec", "wheel_spec"):
        paths = resolve_source_paths(dep_name)
        if paths is not None and len(paths) > 0:
            _deployer_dirty[dep_name] = compute_dirty_hashes(repo_root, path_prefixes=paths)
        else:
            # No source paths: use global dirty hashes (backward compat)
            _deployer_dirty[dep_name] = compute_dirty_hashes(repo_root)

    results = execute_parallel(steps, max_workers=args.jobs)
    output.print_parallel_result(results)

    # Track deployer outcomes for partial-failure state save
    # Also record deployed display names for cycle summary
    successful_deployers: set[str] = set()
    for r in results:
        result_deployer = STEP_TO_DEPLOYER.get(r.name)
        if result_deployer and r.success:
            successful_deployers.add(result_deployer)
            if r.name in STEP_DISPLAY_NAMES:
                deployed_names.append(STEP_DISPLAY_NAMES[r.name])

    # Check for deploy failures (before service restarts)
    failed = [r for r in results if not r.success]
    if failed:
        output.error(f"{len(failed)} deploy step(s) failed: " + ", ".join(r.name for r in failed))
        _total_elapsed = _time.monotonic() - _cycle_start
        output.print_deploy_total(_total_elapsed, success=False)
        # Still save state for successful deployers (partial failure recovery).
        # Preserve the previous diff_base_commit so the next run re-detects
        # the changes that the failed deployer(s) missed.
        build_and_save_state(
            repo_root,
            site.root,
            current_branch,
            successful_deployers,
            state,
            deployer_dirty_hashes=_deployer_dirty,
            all_succeeded=False,
            backend=args.backend or "",
            uncovered_files=uncovered_files,
        )
        return _make_result(1)

    # Service restart gating: only consider services for deployers that ran
    services = resolve_services(changes, targets, site, deployed_deployers=successful_deployers)

    svc_count = 0
    svc_elapsed = 0.0
    svc_failed = False
    if services and not args.no_restart:
        if output.get_verbosity() >= output.Verbosity.VERBOSE:
            output.print_blank()
            output.print_service_preview(services, no_restart=False)
        svc_result = restart_services(services, site, ssh_state)
        svc_count = svc_result.services_restarted
        svc_elapsed = svc_result.elapsed
        if svc_result.services_failed > 0:
            svc_failed = True
            failed_names = ", ".join(svc_result.failures) or "unknown"
            output.error(
                f"DEPLOYED BUT NOT RUNNING: {failed_names} failed to restart "
                f"({svc_result.services_restarted} succeeded) in {svc_result.elapsed:.1f}s"
            )
            output.error(f"  Manual fix: omd restart {' '.join(svc_result.failures)}")
        else:
            output.info(
                f"Services restarted: {svc_result.services_restarted} in {svc_result.elapsed:.1f}s"
            )
    elif services and args.no_restart:
        if output.get_verbosity() >= output.Verbosity.VERBOSE:
            output.print_blank()
        output.print_service_preview(services, no_restart=True)
    elif not args.no_restart and successful_deployers:
        # Deployers ran but their changes don't need any restarts
        output.print_restart_skipped()

    # Save deploy state after deployment
    build_and_save_state(
        repo_root,
        site.root,
        current_branch,
        successful_deployers,
        state,
        deployer_dirty_hashes=_deployer_dirty,
        backend=args.backend or "",
        uncovered_files=uncovered_files,
    )

    # Total deploy time and optional verbose timing table
    _cycle_elapsed = _time.monotonic() - _cycle_start
    _total_elapsed = _cycle_elapsed + manifest_elapsed + overlay_elapsed
    _print_timing_display(
        results,
        _total_elapsed,
        manifest_elapsed,
        overlay_elapsed,
        svc_elapsed,
    )

    # Exit code 2 = deployed but services failed (distinct from 1 = deploy failed)
    exit_code = 2 if svc_failed else 0
    return _make_result(exit_code, services_restarted=svc_count)


def _setup_frontend_supervisor(
    repo_root: Path,
    site: SiteInfo,
    ssh_state: SSHState,
) -> tuple[FrontendSupervisor, FrontendConfig, Path] | int:
    """Shared frontend setup: site check, stale cleanup, supervisor start, .mk override."""
    from cmk.dev_deploy.errors import FrontendError, IBazelError
    from cmk.dev_deploy.frontend.frontend_supervisor import (
        _pid_file,
        FrontendSupervisor,
        IBAZEL_TARGET,
    )
    from cmk.dev_deploy.site.site_config import (
        check_site_running,
        is_stale_override,
        override_mk_path,
        remove_override,
        write_override,
    )
    from cmk.dev_deploy.types import detect_frontend_project, FrontendConfig

    output.set_combined_mode(True)

    if not check_site_running(site.name, ssh_state):
        output.error("Site must be running to use --frontend")
        output.info(f"  Start it with: omd start {site.name}")
        return 1

    mk_path = override_mk_path(site.root)
    if is_stale_override(mk_path, _pid_file(), site.name, ssh_state):
        output.warn("Stale frontend config found, cleaning up")
        remove_override(site.name, mk_path, ssh_state)

    try:
        detect_frontend_project(repo_root)
    except FrontendError as e:
        output.error(str(e))
        return 1

    config = FrontendConfig()
    supervisor = FrontendSupervisor(config, repo_root)

    output.info("Starting frontend supervisor (iBazel)...")
    try:
        supervisor.start()
    except (FrontendError, IBazelError) as e:
        output.error(str(e))
        return 1
    output.success("Frontend supervisor active -- watching for changes")
    output.info(f"  Target: {IBAZEL_TARGET}")
    output.info(f"  Vite: http://localhost:{config.port}/")

    if not write_override(site.name, mk_path, ssh_state):
        output.error("Failed to enable frontend inject mode")
        output.info(f"  Could not write: {mk_path}")
        supervisor.stop()
        return 1
    output.info(f"  Inject mode enabled: {mk_path}")
    output.info(f'  Set load_frontend_vue = "inject" for site {site.name}')

    return supervisor, config, mk_path


def _run_frontend(repo_root: Path, site: SiteInfo, ssh_state: SSHState) -> int:
    """Start iBazel frontend supervisor as foreground blocking process."""
    import time

    from cmk.dev_deploy.errors import FrontendError, IBazelError
    from cmk.dev_deploy.site.site_config import remove_override

    result = _setup_frontend_supervisor(repo_root, site, ssh_state)
    if isinstance(result, int):
        return result
    supervisor, _config, mk_path = result

    try:
        # Block until iBazel exits or user presses Ctrl-C
        while supervisor.is_running():
            time.sleep(0.5)

        # If we get here, iBazel crashed (exited without Ctrl-C)
        crash_lines = supervisor.get_crash_report()
        output.error("iBazel frontend supervisor crashed")
        if crash_lines:
            output.error("Last stderr output:")
            for line in crash_lines:
                output.error(f"  {line}")
        output.info("Recovery: run cmk-dev-deploy --frontend again")
        supervisor.stop()
        return 1

    except (FrontendError, IBazelError) as e:
        output.error(str(e))
        return 1
    except KeyboardInterrupt:
        output.info("Stopping frontend supervisor...")
        remove_override(site.name, mk_path, ssh_state)
        output.info(f"  Inject mode disabled: removed {mk_path}")
        supervisor.stop()
        output.success("Frontend supervisor stopped.")
        return 0
    finally:
        remove_override(site.name, mk_path, ssh_state)
        if supervisor.is_running():
            supervisor.stop()


def _run_frontend_watch(
    args: argparse.Namespace, repo_root: Path, site: SiteInfo, ssh_state: SSHState
) -> int:
    """Combined --frontend --watch: deploy first, start iBazel, enter watch loop."""
    from cmk.dev_deploy.errors import FrontendError, IBazelError
    from cmk.dev_deploy.site.site_config import remove_override

    result = _setup_frontend_supervisor(repo_root, site, ssh_state)
    if isinstance(result, int):
        return result
    supervisor, _config, mk_path = result

    try:
        return watch_loop(
            site,
            repo_root,
            lambda: _run_deploy_cycle(args, repo_root, site, ssh_state),
            supervisor=supervisor,
        )
    except (FrontendError, IBazelError) as e:
        output.error(f"[frontend] {e}")
        return 1
    except KeyboardInterrupt:
        output.info("Stopping frontend supervisor and watch mode...")
        remove_override(site.name, mk_path, ssh_state)
        output.info(f"  Inject mode disabled: removed {mk_path}")
        supervisor.stop()
        output.success("Frontend supervisor stopped.")
        return 0
    finally:
        remove_override(site.name, mk_path, ssh_state)
        if supervisor.is_running():
            supervisor.stop()


def _infer_phase(error: BaseException) -> str:
    from cmk.dev_deploy.errors import (
        BazelBuildError,
        CloneError,
        ConfigDeployError,
        FrontendError,
        IBazelError,
        OverlayError,
        WheelDeployError,
    )

    phase_map: dict[type, str] = {
        ManifestBuildError: "manifest_build",
        ChangeDetectionError: "change_detection",
        OverlayError: "overlay",
        CloneError: "clone",
        SudoersError: "sudoers",
        BazelBuildError: "bazel_build",
        ConfigDeployError: "config_deploy",
        WheelDeployError: "wheel_deploy",
        FrontendError: "frontend",
        IBazelError: "ibazel",
    }
    return phase_map.get(type(error), "unknown")


def _guard_terminal_settings() -> None:
    """Save terminal settings and restore them on exit."""
    try:
        fd = sys.stderr.fileno()
        saved = termios.tcgetattr(fd)
    except (termios.error, OSError, ValueError):
        return

    def _restore() -> None:
        try:
            termios.tcsetattr(fd, termios.TCSANOW, saved)
        except (termios.error, OSError, ValueError):
            pass

    atexit.register(_restore)


def main(argv: list[str] | None = None) -> int:
    """Run the cmk-dev-deploy CLI."""
    if os.getuid() == 0:
        output.error("cmk-dev-deploy must not be run as root.")
        return 1
    _guard_terminal_settings()
    args = parse_args(argv)
    output.set_verbosity(args.verbose)

    try:
        repo_root = find_repo_root()
    except RepoNotFoundError as e:
        output.error(str(e))
        return 1

    # --print-setup / --remove-setup only need the site name; they exit
    # before any manifest, sudo, or site preparation work.
    if args.print_setup or args.remove_setup:
        from cmk.dev_deploy.site import sudoers
        from cmk.dev_deploy.site.site_resolver import resolve_site_name

        flag = "--print-setup" if args.print_setup else "--remove-setup"
        site_name = resolve_site_name(args.site, repo_root, Path.cwd())
        if site_name is None:
            output.error(
                f"No site found.\n  Specify explicitly: cmk-dev-deploy {flag} --site SITENAME"
            )
            return 1
        try:
            if args.print_setup:
                sudoers.print_setup(site_name)
            else:
                sudoers.remove_setup(site_name)
        except SudoersError as e:
            output.error(str(e))
            return 1
        return 0

    # --purge only needs the site root path, not full site resolution.
    # This allows purging even if the site is partially deleted (or removed
    # via ``omd rm``).  We try the lightweight find_site_root first, then
    # fall back to the normal name resolution chain (.site file, $SITE,
    # omd sites), and finally scan the overlay directory for orphaned data.
    if args.purge:
        from cmk.dev_deploy.site.site_resolver import find_site_root, resolve_site_name

        site_name = resolve_site_name(args.site, repo_root, Path.cwd())
        site_root = find_site_root(site_name)

        # Last resort: scan the deploy data dirs for orphaned site data
        # (overlay upper layers / deploy state, version clones).
        if site_root is None:
            from cmk.dev_deploy.site.sudoers import DEV_VERSIONS_DIR

            overlay_base = Path("/var/tmp/cmk-dev-deploy")  # nosec B108 # BNS:59d87e
            candidates: set[str] = set()
            for base in (overlay_base, DEV_VERSIONS_DIR):
                if base.is_dir():
                    # Hidden dirs (e.g. the .uv-cache next to the clones)
                    # are not site data.
                    candidates.update(
                        d.name for d in base.iterdir() if d.is_dir() and not d.name.startswith(".")
                    )
            if len(candidates) == 1:
                orphan = next(iter(candidates))
                site_root = Path("/omd/sites") / orphan
                output.info(f"Site deleted but deploy data found for '{orphan}'")
            elif len(candidates) > 1:
                output.error(
                    f"Orphaned deploy data found for several sites: "
                    f"{', '.join(sorted(candidates))}\n"
                    "  Specify which to purge: cmk-dev-deploy --purge --site SITENAME"
                )
                return 1

        if site_root is None:
            output.error(
                "No site found to purge.\n"
                "  Specify explicitly: cmk-dev-deploy --purge --site SITENAME"
            )
            return 1
        from cmk.dev_deploy.site.preparation import create_backend, resolve_backend_name

        # Read the state before teardown -- teardown removes the state file.
        state = load_state(site_root)
        backend = create_backend(
            resolve_backend_name(args.backend, state.backend if state else "", site_root),
            SSHState(),
        )
        try:
            backend.teardown(site_root)
        except DeployError as e:
            output.error(str(e))
            return 1
        # The site is back on pristine code; stale incremental state must
        # not survive. (The overlay teardown already removed the whole
        # state dir; for the clone backend this deletes the state file.)
        delete_state(site_root)
        output.success(
            f"{backend.name.capitalize()} purged. Site reverted to original state (stopped)."
        )
        output.info(f"  Start with: omd start {site_root.name}")
        return 0

    try:
        site = resolve_site(args.site, repo_root, Path.cwd())
    except (SiteNotFoundError, SiteError) as e:
        output.error(str(e))
        return 1

    output.open_log_file(site.name)
    try:
        return _main_with_site(args, repo_root, site)
    except DeployError as e:
        from cmk.dev_deploy.core.diagnostics import capture_diagnostic_bundle

        capture_diagnostic_bundle(
            e,
            site=site,
            repo_root=repo_root,
            phase=_infer_phase(e),
            json_errors=getattr(args, "json_errors", False),
        )
        return 1
    finally:
        output.close_log_file()


def _main_with_site(args: argparse.Namespace, repo_root: Path, site: SiteInfo) -> int:
    import time as _time

    from cmk.dev_deploy.manifest.staleness import ensure_manifest
    from cmk.dev_deploy.site.preparation import (
        check_backend_conflict,
        create_backend,
        resolve_backend_name,
    )

    if output.get_verbosity() >= output.Verbosity.VERBOSE:
        output.print_blank()
        output.info("Detected site:")
        output.print_site_info(site)
    else:
        output.info(f"Site: {output.BOLD}{site.name}{output.RESET} ({site.edition.value})")

    if args.info:
        return 0

    if args.commit:
        output.info(f"Deploying state at commit {args.commit}")

    # --dry-run only needs the manifest (for change categorization) and
    # deploy state (in /var/tmp/, not on the overlay).  Skip sudo and
    # overlay setup entirely — dry-run never writes to the site.
    if args.dry_run:
        t0 = _time.monotonic()
        ensure_manifest(repo_root, force_rebuild=args.rebuild_manifest)
        _manifest_elapsed = _time.monotonic() - t0
        ssh_state = SSHState()
        return _run_deploy_cycle(args, repo_root, site, ssh_state, _manifest_elapsed).exit_code

    ssh_state = SSHState()

    # Backend selection: explicit flag > deploy-state record > default.
    # Resolved once here; the cycle records it back into the deploy state.
    state = load_state(site.root)
    backend = create_backend(
        resolve_backend_name(args.backend, state.backend if state else "", site.root), ssh_state
    )
    args.backend = backend.name

    if (conflict := check_backend_conflict(backend.name, site.root)) is not None:
        output.error(conflict)
        return 1

    # Acquire privileges early — before the manifest rebuild which can
    # take minutes (and would e.g. expire a sudo timestamp).
    try:
        backend.prepare_privileges(site.root, full=args.full)
    except SudoersError as e:
        # Missing consent is not a crash — no diagnostic bundle.
        output.error(str(e))
        return 1

    if backend.name == "clone":
        # The clone backend injects no SSH key. Pre-seed the SSH cache so
        # run_as_site_user() (service restarts, frontend override writes)
        # skips the SSH probe and goes straight to its sudo fallback, which
        # the just-probed sudoers rule makes passwordless.
        ssh_state.ssh_available[site.name] = False

    # Manifest must be ready before site preparation because capability
    # restoration during ensure() reads it.
    t0 = _time.monotonic()
    ensure_manifest(repo_root, force_rebuild=args.rebuild_manifest)
    _manifest_elapsed = _time.monotonic() - t0

    t0 = _time.monotonic()
    if args.full:
        backend.teardown(site.root)
    backend.ensure(site.root)
    _overlay_elapsed = _time.monotonic() - t0

    # Branch mismatch warning
    branch_warning = check_branch_mismatch(site.build_commit, repo_root)
    if branch_warning:
        output.warn(branch_warning)

    # Combined --frontend --watch mode
    if args.frontend and args.watch:
        result = _run_deploy_cycle(
            args, repo_root, site, ssh_state, _manifest_elapsed, _overlay_elapsed
        )
        if result.exit_code != 0:
            output.error("Deploy failed. Not starting frontend dev server.")
            return result.exit_code
        return _run_frontend_watch(args, repo_root, site, ssh_state)

    # Watch mode: enter polling loop with deploy_fn wrapping _run_deploy_cycle
    if args.watch:
        return watch_loop(
            site,
            repo_root,
            lambda: _run_deploy_cycle(args, repo_root, site, ssh_state),
        )

    # One-shot deploy
    result = _run_deploy_cycle(
        args, repo_root, site, ssh_state, _manifest_elapsed, _overlay_elapsed
    )

    # Frontend supervisor: deploy first, then start Vite
    if args.frontend:
        if result.exit_code != 0:
            output.error("Deploy failed. Not starting frontend dev server.")
            return result.exit_code
        return _run_frontend(repo_root, site, ssh_state)

    return result.exit_code


if __name__ == "__main__":
    sys.exit(main())
