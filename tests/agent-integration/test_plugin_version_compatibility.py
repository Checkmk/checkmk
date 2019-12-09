# pylint: disable=redefined-outer-name

import pytest  # type: ignore
import docker  # type: ignore

import testlib
import testlib.pylint_cmk


@pytest.fixture(scope="module")
def docker_client():
    return docker.DockerClient()


@pytest.fixture(scope="module")
def python_container(request, docker_client):
    c = docker_client.containers.run(
        image="shimizukawa/python-all",
        command=["python2.5", "-c", "import time; time.sleep(9999)"],
        detach=True,
        volumes={
            testlib.cmk_path(): {
                'bind': '/cmk',
                'mode': 'ro'
            },
        },
    )
    yield c
    c.remove(force=True)


def _get_python_plugins():
    return [
        "agents/plugins/%s" % f
        for f in testlib.pylint_cmk.get_pylint_files("%s/agents/plugins" % testlib.cmk_path(), "*")
    ]


@pytest.mark.parametrize("plugin_path", _get_python_plugins())
@pytest.mark.parametrize("python_version", ["2.5", "2.6", "2.7"])
def test_agent_plugin_syntax_compatibility(python_container, plugin_path, python_version):
    _exit_code, output = python_container.exec_run(
        ["python%s" % python_version,
         "%s/%s" % (testlib.cmk_path(), plugin_path)],
        workdir="/cmk",
    )

    assert "SyntaxError: " not in output
