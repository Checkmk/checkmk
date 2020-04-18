#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import errno
import logging
import multiprocessing
import os
import pprint
import shutil
import signal
import sys
import time
import traceback
from types import FrameType  # pylint: disable=unused-import
import io

from typing import Tuple, Callable, Type, List, Text, Optional, Union, Dict, Any  # pylint: disable=unused-import
import psutil  # type: ignore[import]

if sys.version_info[0] >= 3:
    from pathlib import Path  # pylint: disable=import-error
else:
    from pathlib2 import Path  # pylint: disable=import-error

import six

import cmk.utils.log
from cmk.utils.log import VERBOSE
import cmk.utils.daemon as daemon
import cmk.utils.store as store
from cmk.utils.exceptions import MKGeneralException, MKTerminate

import cmk.gui.log
from cmk.gui.i18n import _

JobId = str
JobParameters = Dict[str, Any]
JobStatusSpec = Dict[str, Any]


class BackgroundJobAlreadyRunning(MKGeneralException):
    pass


#.
#   .--Function Interface--------------------------------------------------.
#   |               _____                 _   _                            |
#   |              |  ___|   _ _ __   ___| |_(_) ___  _ __                 |
#   |              | |_ | | | | '_ \ / __| __| |/ _ \| '_ \                |
#   |              |  _|| |_| | | | | (__| |_| | (_) | | | |               |
#   |              |_|   \__,_|_| |_|\___|\__|_|\___/|_| |_|               |
#   |                                                                      |
#   |              ___       _             __                              |
#   |             |_ _|_ __ | |_ ___ _ __ / _| __ _  ___ ___               |
#   |              | || '_ \| __/ _ \ '__| |_ / _` |/ __/ _ \              |
#   |              | || | | | ||  __/ |  |  _| (_| | (_|  __/              |
#   |             |___|_| |_|\__\___|_|  |_|  \__,_|\___\___|              |
#   |                                                                      |
#   +----------------------------------------------------------------------+


class BackgroundProcessInterface(object):
    def __init__(self, job_parameters):
        # type: (JobParameters) -> None
        super(BackgroundProcessInterface, self).__init__()
        self._job_parameters = job_parameters

    def get_work_dir(self):
        # type: () -> str
        return self._job_parameters["work_dir"]

    def get_job_id(self):
        # type: () -> str
        return self._job_parameters["job_id"]

    def get_logger(self):
        # type: () -> logging.Logger
        return self._job_parameters["logger"]

    def send_progress_update(self, info):
        # type: (Union[Text, str]) -> None
        """ The progress update is written to stdout and will be catched by the threads counterpart """
        sys.stdout.write(six.ensure_str(info) + "\n")

    def send_result_message(self, info):
        # type: (Union[Text, str]) -> None
        """ The result message is written to stdout because of log output clarity
        as well as into a distinct file, to separate this info from the rest of the context information"""
        encoded_info = "%s\n" % six.ensure_str(info)
        sys.stdout.write(encoded_info)

        result_message_path = Path(
            self.get_work_dir()) / BackgroundJobDefines.result_message_filename
        with result_message_path.open("ab") as f:
            f.write(six.ensure_binary(encoded_info))

    def send_exception(self, info):
        # type: (Union[Text, str]) -> None
        """ Exceptions are written to stdout because of log output clarity
        as well as into a distinct file, to separate this info from the rest of the context information"""
        # Exceptions also get an extra newline, since some error messages tend not output a \n at the end..
        encoded_info = "%s\n" % six.ensure_str(info)
        sys.stdout.write(encoded_info)
        with (Path(self.get_work_dir()) / BackgroundJobDefines.exceptions_filename).open("ab") as f:
            f.write(six.ensure_binary(encoded_info))


#.
#   .--Background Process--------------------------------------------------.
#   |       ____             _                                   _         |
#   |      | __ )  __ _  ___| | ____ _ _ __ ___  _   _ _ __   __| |        |
#   |      |  _ \ / _` |/ __| |/ / _` | '__/ _ \| | | | '_ \ / _` |        |
#   |      | |_) | (_| | (__|   < (_| | | | (_) | |_| | | | | (_| |        |
#   |      |____/ \__,_|\___|_|\_\__, |_|  \___/ \__,_|_| |_|\__,_|        |
#   |                            |___/                                     |
#   |                  ____                                                |
#   |                 |  _ \ _ __ ___   ___ ___  ___ ___                   |
#   |                 | |_) | '__/ _ \ / __/ _ \/ __/ __|                  |
#   |                 |  __/| | | (_) | (_|  __/\__ \__ \                  |
#   |                 |_|   |_|  \___/ \___\___||___/___/                  |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   | When started, BackgroundJob spawns one instance of BackgroundProcess |
#   '----------------------------------------------------------------------'


class BackgroundProcess(BackgroundProcessInterface, multiprocessing.Process):
    def __init__(self, job_parameters):
        # type: (JobParameters) -> None
        super(BackgroundProcess, self).__init__(job_parameters)
        self._jobstatus = self._job_parameters["jobstatus"]
        # TODO: Hand over the logger via arguments
        self._logger = cmk.gui.log.logger.getChild("background_process")
        self._job_parameters["logger"] = self._logger

    def _register_signal_handlers(self):
        # type: () -> None
        self._logger.debug("Register signal handler %d", os.getpid())
        signal.signal(signal.SIGTERM, self._handle_sigterm)

    def _handle_sigterm(self, signum, frame):
        # type: (int, Optional[FrameType]) -> None
        self._logger.debug("Received SIGTERM")
        status = self._jobstatus.get_status_from_file()
        if not status.get("stoppable", True):
            self._logger.warning("Skip termination of background job (Job ID: %s, PID: %d)",
                                 self._job_parameters["job_id"], os.getpid())
            return

        raise MKTerminate()

    def run(self):
        # type: () -> None
        # Detach from parent and cleanup inherited file descriptors
        os.setsid()
        daemon.set_procname(six.ensure_binary(BackgroundJobDefines.process_name))
        sys.stdin.close()
        sys.stdout.close()
        sys.stderr.close()
        daemon.closefrom(0)

        try:
            self.initialize_environment()
            self._logger.log(VERBOSE, "Initialized background job (Job ID: %s)",
                             self._job_parameters["job_id"])
            self._jobstatus.update_status({
                "pid": self.pid,
                "state": JobStatusStates.RUNNING,
            })

            # The actual function call
            self._execute_function()

            # Final status update
            job_status = self._jobstatus.get_status_from_file()

            if job_status.get("loginfo", {}).get("JobException"):
                final_state = JobStatusStates.EXCEPTION
            else:
                final_state = JobStatusStates.FINISHED

            self._jobstatus.update_status({
                "state": final_state,
                "duration": time.time() - job_status["started"],
            })
        except MKTerminate:
            self._logger.warning("Job was stopped")
            self._jobstatus.update_status({"state": JobStatusStates.STOPPED})
        except Exception:
            self._logger.error("Exception while preparing background function environment",
                               exc_info=True)
            self._jobstatus.update_status({"state": JobStatusStates.EXCEPTION})

    def initialize_environment(self):
        # type: () -> None
        """Setup environment (Logging, Livestatus handles, etc.)"""
        self._open_stdout_and_stderr()
        self._enable_logging_to_stdout()
        self._register_signal_handlers()

    def _execute_function(self):
        # type: () -> None
        func_ptr, args, kwargs = self._job_parameters["function_parameters"]
        job_interface = BackgroundProcessInterface(self._job_parameters)
        kwargs["job_interface"] = job_interface

        try:
            func_ptr(*args, **kwargs)
        except MKTerminate:
            raise
        except Exception as e:
            self._logger.exception("Exception in background function")
            job_interface.send_exception(_("Exception: %s") % (e))

    def _open_stdout_and_stderr(self):
        # type: () -> None
        """Create a temporary file and use it as stdout / stderr buffer"""
        # - We can not use io.BytesIO() or similar because we need real file descriptors
        #   to be able to catch the (debug) output of libraries like libldap or subproccesses
        # - Use buffering=0 to make the non flushed output directly visible in
        #   the job progress dialog
        # - Python 3's stdout and stderr expect 'str' not 'bytes'
        unbuffered = (Path(self.get_work_dir()) /
                      BackgroundJobDefines.progress_update_filename).open("wb", buffering=0)

        if sys.version_info[0] >= 3:
            sys.stdout = sys.stderr = io.TextIOWrapper(unbuffered, write_through=True)
        else:
            sys.stdout = sys.stderr = unbuffered

        os.dup2(sys.stdout.fileno(), 1)
        os.dup2(sys.stderr.fileno(), 2)

    def _enable_logging_to_stdout(self):
        # type: () -> None
        """In addition to the web.log we also want to see the job specific logs
        in stdout (which results in job progress info)"""
        handler = logging.StreamHandler(stream=sys.stdout)
        handler.setFormatter(cmk.utils.log.get_formatter())
        cmk.gui.log.logger.addHandler(handler)


class BackgroundJobDefines(object):
    base_dir = os.path.join(cmk.utils.paths.var_dir, "background_jobs")
    process_name = "cmk-job"  # NOTE: keep this name short! psutil.Process tends to truncate long names

    jobstatus_filename = "jobstatus.mk"
    progress_update_filename = "progress_update"
    exceptions_filename = "exceptions"
    result_message_filename = "result_message"


#.
#   .--Background Job------------------------------------------------------.
#   |       ____             _                                   _         |
#   |      | __ )  __ _  ___| | ____ _ _ __ ___  _   _ _ __   __| |        |
#   |      |  _ \ / _` |/ __| |/ / _` | '__/ _ \| | | | '_ \ / _` |        |
#   |      | |_) | (_| | (__|   < (_| | | | (_) | |_| | | | | (_| |        |
#   |      |____/ \__,_|\___|_|\_\__, |_|  \___/ \__,_|_| |_|\__,_|        |
#   |                            |___/                                     |
#   |                              _       _                               |
#   |                             | | ___ | |__                            |
#   |                          _  | |/ _ \| '_ \                           |
#   |                         | |_| | (_) | |_) |                          |
#   |                          \___/ \___/|_.__/                           |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   |                                                                      |
#   '----------------------------------------------------------------------'


class BackgroundJob(object):
    _background_process_class = BackgroundProcess
    housekeeping_max_age_sec = 86400 * 30
    housekeeping_max_count = 50

    # TODO: Make this an abstract property
    job_prefix = "unnamed-job"

    def __init__(self, job_id, logger=None, **kwargs):
        # type: (str, logging.Logger, **Any) -> None
        super(BackgroundJob, self).__init__()
        self._job_id = job_id
        self._job_base_dir = BackgroundJobDefines.base_dir
        self._job_initializiation_lock = os.path.join(self._job_base_dir, "job_initialization.lock")

        if not logger:
            raise MKGeneralException(_("The background job is missing a logger instance"))
        self._logger = logger

        kwargs.setdefault("stoppable", True)

        self._kwargs = kwargs
        self._work_dir = os.path.join(self._job_base_dir, self._job_id)
        self._jobstatus = JobStatus(self._work_dir)

        # The function ptr and its args/kwargs
        self._queued_function = None  # type: Optional[Tuple[Callable, Tuple[Any, ...], Dict[str, Any]]]

    def get_job_id(self):
        # type: () -> str
        return self._job_id

    def get_title(self):
        # type: () -> Text
        return self._jobstatus.get_status_from_file().get("title", _("Background job"))

    def get_work_dir(self):
        # type: () -> str
        return self._work_dir

    def exists(self):
        # type: () -> bool
        return os.path.exists(self._work_dir) and self._jobstatus.statusfile_exists()

    def is_available(self):
        # type: () -> bool
        return self.exists()

    def is_stoppable(self):
        # type: () -> bool
        return self._jobstatus.get_status_from_file().get("stoppable", True)

    def _verify_running(self, job_status):
        # type: (JobStatusSpec) -> bool
        if job_status["state"] == JobStatusStates.INITIALIZED:
            # The process was created a millisecond ago
            # The child process however, did not have time to update the statefile with its PID
            # We consider this scenario as OK, if the start time was recent enough
            if time.time() - job_status["started"] < 5:  # 5 seconds
                return True

        if job_status["pid"] is None:
            return False

        try:
            p = psutil.Process(job_status["pid"])
            if self._is_correct_process(job_status, p):
                return True
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            return False

        return False

    def is_active(self):
        # type: () -> bool
        if not self.exists():
            return False

        job_status = self.get_status()
        return job_status["is_active"] and self._verify_running(job_status)

    def update_status(self, new_data):
        # type: (JobStatusSpec) -> None
        self._jobstatus.update_status(new_data)

    def stop(self):
        # type: () -> None
        if not self.is_active():
            raise MKGeneralException(_("Job already finished"))

        if not self.is_stoppable():
            raise MKGeneralException(_("This job cannot be stopped"))

        self._terminate_processes()

        job_status = self._jobstatus.get_status_from_file()
        duration = time.time() - job_status["started"]
        self._jobstatus.update_status({
            "state": JobStatusStates.STOPPED,
            "duration": duration,
        })

    def delete(self):
        # type: () -> None
        if not self.is_stoppable() and self.is_active():
            raise MKGeneralException(_("Cannot delete job. Job cannot be stopped."))

        self._terminate_processes()
        self._delete_work_dir()

    def _delete_work_dir(self):
        # type: () -> None
        try:
            shutil.rmtree(self._work_dir)
        except OSError as e:
            if e.errno == errno.ENOENT:
                pass
            else:
                raise

    def _terminate_processes(self):
        # type: () -> None
        job_status = self.get_status()

        if job_status["pid"] is None:
            return

        # Send SIGTERM
        self._logger.debug("Stopping job using SIGTERM \"%s\" (PID: %s)", self._job_id,
                           job_status["pid"])
        try:
            process = psutil.Process(job_status["pid"])
            if not self._is_correct_process(job_status, process):
                return
            process.send_signal(signal.SIGTERM)
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            return

        self._logger.debug("Waiting for job")
        start_time = time.time()
        while time.time() - start_time < 10:  # 10 seconds SIGTERM grace period
            job_still_running = False
            try:
                process = psutil.Process(job_status["pid"])
                if not self._is_correct_process(job_status, process):
                    return
                job_still_running = True
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                return

            if not job_still_running:
                break
            time.sleep(0.1)

        try:
            p = psutil.Process(job_status["pid"])
            if self._is_correct_process(job_status, process):
                # Kill unresponsive jobs
                self._logger.debug("Killing job")
                p.send_signal(signal.SIGKILL)
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            return

    def _is_correct_process(self, job_status, psutil_process):
        # type: (JobStatusSpec, psutil.Process) -> bool
        if psutil_process.name() != BackgroundJobDefines.process_name:
            return False

        return True

    def get_status(self):
        # type: () -> JobStatusSpec
        status = self._jobstatus.get_status_from_file()

        # Some dynamic stuff
        if status.get("state", "") == JobStatusStates.RUNNING and status["pid"] is not None:
            try:
                p = psutil.Process(status["pid"])
                if not self._is_correct_process(status, p):
                    status["state"] = JobStatusStates.STOPPED
                else:
                    status["duration"] = time.time() - status["started"]
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                status["state"] = JobStatusStates.STOPPED

        if "state" not in status:
            status["state"] = JobStatusStates.INITIALIZED
            status["started"] = time.time()

        return status

    # TODO: Clean this up (functions are registered by subclassing, no need to register them here)
    def set_function(self, func_ptr, *args, **kwargs):
        # type: (Callable, *Any, **Any) -> None
        self._queued_function = (func_ptr, args, kwargs)

    def start(self):
        # type: () -> None
        try:
            store.aquire_lock(self._job_initializiation_lock)
            self._start()
        finally:
            store.release_lock(self._job_initializiation_lock)

    def _start(self):
        # type: () -> None
        if self.is_active():
            raise BackgroundJobAlreadyRunning(_("Background Job %s already running") % self._job_id)

        self._prepare_work_dir()

        # Start processes
        initial_status = {
            "state": JobStatusStates.INITIALIZED,
            "statusfile": str(Path(self._job_id) / BackgroundJobDefines.jobstatus_filename),
            "started": time.time(),
            "duration": 0.0,
        }
        initial_status.update(self._kwargs)
        self._jobstatus.update_status(initial_status)

        job_parameters = {}  # type: JobParameters
        job_parameters["work_dir"] = self._work_dir
        job_parameters["job_id"] = self._job_id
        job_parameters["jobstatus"] = self._jobstatus
        job_parameters["function_parameters"] = self._queued_function
        p = multiprocessing.Process(target=self._start_background_subprocess,
                                    args=(job_parameters,))

        p.start()
        p.join()

        if p.exitcode == 0:
            job_status = self.get_status()
            self._logger.debug("Started job \"%s\" (PID: %s)", self._job_id, job_status["pid"])

    def _prepare_work_dir(self):
        # type: () -> None
        self._delete_work_dir()
        os.makedirs(self._work_dir)

    def _start_background_subprocess(self, job_parameters):
        # type: (JobParameters) -> None
        try:
            # Even the "short living" intermediate process here needs to close
            # the inherited file descriptors as soon as possible to prevent
            # race conditions with inherited locks that have been inherited
            # from the parent process. The job_initialization.lock is such a
            # thing we had a problem with when background jobs were initialized
            # while the apache tried to stop / restart.
            #
            # Had problems with closefrom() during the tests. Explicitly
            # closing the locks here instead of closing all fds to keep logging
            # related fds open.
            #daemon.closefrom(3)
            store.release_all_locks()

            self._jobstatus.update_status({"ppid": os.getpid()})

            p = self._background_process_class(job_parameters)
            p.start()
        except Exception as e:
            self._logger.exception("Error while starting subprocess: %s", e)
            os._exit(1)
        os._exit(0)


class JobStatusStates(object):
    INITIALIZED = "initialized"
    RUNNING = "running"
    FINISHED = "finished"
    STOPPED = "stopped"
    EXCEPTION = "exception"


class JobStatus(object):
    def __init__(self, work_dir):
        # type: (str) -> None
        super(JobStatus, self).__init__()
        self._work_dir = work_dir
        self._jobstatus_path = Path(work_dir) / BackgroundJobDefines.jobstatus_filename

        self._progress_update_path = Path(work_dir) / BackgroundJobDefines.progress_update_filename
        self._result_message_path = Path(work_dir) / BackgroundJobDefines.result_message_filename
        self._exceptions_path = Path(work_dir) / BackgroundJobDefines.exceptions_filename

    def get_status_from_file(self):
        # type: () -> JobStatusSpec
        if not self._jobstatus_path.exists():
            data = {}  # type: JobStatusSpec
            data["state"] = "initialized"
        else:
            try:
                # Read this data with an explicit lock
                # This prevents a race condition where an empty jobstatus.mk file is read
                data = store.load_object_from_file(str(self._jobstatus_path), default={}, lock=True)

                # Repair broken/invalid files
                if "state" not in data:
                    data["state"] = "initialized"
                    data["started"] = time.time()
            finally:
                store.release_lock(str(self._jobstatus_path))

        data.setdefault("pid", None)
        data["loginfo"] = {}
        for field_id, field_path in [("JobProgressUpdate", self._progress_update_path),
                                     ("JobResult", self._result_message_path),
                                     ("JobException", self._exceptions_path)]:
            if field_path.exists():
                with field_path.open(encoding="utf-8") as f:
                    data["loginfo"][field_id] = f.read().splitlines()
            else:
                data["loginfo"][field_id] = []

        map_substate_to_active = {
            JobStatusStates.INITIALIZED: True,
            JobStatusStates.RUNNING: True,
            JobStatusStates.FINISHED: False,
            JobStatusStates.STOPPED: False,
            JobStatusStates.EXCEPTION: False
        }
        data["is_active"] = map_substate_to_active[data["state"]]
        return data

    def statusfile_exists(self):
        # type: () -> bool
        return self._jobstatus_path.exists()

    def update_status(self, params):
        # type: (JobStatusSpec) -> None
        if not self._jobstatus_path.parent.exists():
            return

        if params:
            try:
                status = store.load_object_from_file(str(self._jobstatus_path), {}, lock=True)
                status.update(params)
                store.save_mk_file(str(self._jobstatus_path), self._format_value(status))
            finally:
                store.release_lock(str(self._jobstatus_path))

    def _format_value(self, value):
        # type: (Any) -> str
        return pprint.pformat(value)


class BackgroundJobManager(object):
    def __init__(self, logger):
        # type: (logging.Logger) -> None
        self._logger = logger.getChild("job_manager")
        super(BackgroundJobManager, self).__init__()

    def get_running_job_ids(self, job_class):
        # type: (Type[BackgroundJob]) -> List[JobId]
        """Checks for running jobs in the jobs default basedir"""
        all_jobs = self.get_all_job_ids(job_class)
        return [
            job_id for job_id in all_jobs if BackgroundJob(job_id, logger=self._logger).is_active()
        ]

    def get_all_job_ids(self, job_class):
        # type: (Type[BackgroundJob]) -> List[JobId]
        """Checks for running jobs in the jobs default basedir"""
        job_ids = []  # type: List[JobId]
        if not os.path.exists(BackgroundJobDefines.base_dir):
            return job_ids

        for dirname in sorted(os.listdir(BackgroundJobDefines.base_dir)):
            if not dirname.startswith(job_class.job_prefix):
                continue
            job_ids.append(dirname)

        return job_ids

    def do_housekeeping(self, job_classes):
        # type: (List[Type[BackgroundJob]]) -> None
        try:
            for job_class in job_classes:
                job_ids = self.get_all_job_ids(job_class)
                max_age = job_class.housekeeping_max_age_sec
                max_count = job_class.housekeeping_max_count
                all_jobs = []

                job_instances = {}
                for job_id in job_ids:
                    job_instances[job_id] = BackgroundJob(job_id, self._logger)
                    all_jobs.append((job_id, job_instances[job_id].get_status()))
                all_jobs.sort(key=lambda x: x[1]["started"], reverse=True)

                for entry in all_jobs[-1:0:-1]:
                    job_id, job_status = entry
                    if job_status["state"] == JobStatusStates.RUNNING:
                        continue

                    if len(all_jobs) > max_count or (time.time() - job_status["started"] > max_age):
                        job_instances[job_id].delete()
                        all_jobs.remove(entry)
        except Exception:
            self._logger.error(traceback.format_exc())
