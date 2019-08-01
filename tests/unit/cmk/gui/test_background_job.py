import logging
import time
import multiprocessing
import sys
import pytest  # type: ignore
import testlib  # type: ignore

import cmk.utils.paths
import cmk.gui.background_job as background_job
import cmk.gui.gui_background_job as gui_background_job
# Loads all GUI modules
import cmk.gui.modules  # pylint: disable=unused-import

import cmk.gui.log


@pytest.fixture(autouse=True)
def debug_logging():
    cmk.gui.log.set_log_levels({"cmk.web": logging.DEBUG})
    yield
    cmk.gui.log.set_log_levels({"cmk.web": logging.INFO})


def test_registered_background_jobs():
    assert sorted(gui_background_job.job_registry.keys()) == sorted([
        'ParentScanBackgroundJob',
        'BakeAgentsBackgroundJob',
        'DummyBackgroundJob',
        'RenameHostsBackgroundJob',
        'ReportingBackgroundJob',
        'RenameHostBackgroundJob',
        'FetchAgentOutputBackgroundJob',
        'BulkDiscoveryBackgroundJob',
        'UserSyncBackgroundJob',
        'ServiceDiscoveryBackgroundJob',
    ])


def test_registered_background_jobs_attributes():
    for job_class in gui_background_job.job_registry.values():
        assert isinstance(job_class.job_prefix, str)
        assert isinstance(job_class.gui_title(), unicode)


@pytest.fixture(autouse=True)
def job_base_dir(tmp_path, monkeypatch):
    var_dir = tmp_path

    log_dir = var_dir / "log"
    log_dir.mkdir()  # pylint: disable=no-member

    job_dir = var_dir / "background_jobs"
    job_dir.mkdir()  # pylint: disable=no-member

    # Patch for web.log. Sholdn't we do this for all web tests?
    monkeypatch.setattr(cmk.utils.paths, "log_dir", str(log_dir))

    monkeypatch.setattr(background_job.BackgroundJobDefines, "base_dir", str(job_dir))
    return job_dir


@gui_background_job.job_registry.register
class DummyBackgroundJob(gui_background_job.GUIBackgroundJob):
    job_prefix = "dummy_job"

    @classmethod
    def gui_title(cls):
        return u"Dummy Job"

    def __init__(self):
        kwargs = {}
        kwargs["title"] = self.gui_title()
        kwargs["deletable"] = False
        kwargs["stoppable"] = True
        self.finish_hello_event = multiprocessing.Event()

        super(DummyBackgroundJob, self).__init__(self.job_prefix, **kwargs)

    def execute_hello(self, job_interface):
        sys.stdout.write("Hallo :-)\n")
        sys.stdout.flush()
        self.finish_hello_event.wait()

    def execute_endless(self, job_interface):
        sys.stdout.write("Hanging loop\n")
        sys.stdout.flush()
        time.sleep(100)


def test_start_job():
    job = DummyBackgroundJob()
    job.set_function(job.execute_hello)

    status = job.get_status()
    assert status["state"] == background_job.JobStatusStates.INITIALIZED

    job.start()
    testlib.wait_until(job.is_active, timeout=5, interval=0.1)

    with pytest.raises(background_job.BackgroundJobAlreadyRunning):
        job.start()
    assert job.is_active()

    job.finish_hello_event.set()

    testlib.wait_until(
        lambda: job.get_status()["state"] not in
        [background_job.JobStatusStates.INITIALIZED, background_job.JobStatusStates.RUNNING],
        timeout=5,
        interval=0.1)

    status = job.get_status()
    assert status["state"] == background_job.JobStatusStates.FINISHED

    output = "\n".join(status["loginfo"]["JobProgressUpdate"])
    assert "Initialized background job" in output
    assert "Hallo :-)" in output


def test_stop_job():
    job = DummyBackgroundJob()
    job.set_function(job.execute_endless)
    job.start()

    testlib.wait_until(lambda: "Hanging loop" in job.get_status()["loginfo"]["JobProgressUpdate"],
                       timeout=5,
                       interval=0.1)

    status = job.get_status()
    assert status["state"] == background_job.JobStatusStates.RUNNING

    job.stop()

    status = job.get_status()
    assert status["state"] == background_job.JobStatusStates.STOPPED

    output = "\n".join(status["loginfo"]["JobProgressUpdate"])
    assert "Job was stopped" in output
