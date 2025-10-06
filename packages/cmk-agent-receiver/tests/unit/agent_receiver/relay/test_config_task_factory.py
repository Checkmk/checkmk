import pytest

from cmk.agent_receiver.config import Config
from cmk.agent_receiver.relay.api.routers.tasks.libs.config_task_factory import ConfigTaskFactory
from cmk.agent_receiver.relay.api.routers.tasks.libs.tasks_repository import (
    RelayConfigSpec,
    TasksRepository,
)
from cmk.agent_receiver.relay.lib.relays_repository import RelaysRepository
from cmk.agent_receiver.relay.lib.site_auth import InternalAuth
from cmk.testlib.agent_receiver.config_file_system import create_config_folder


@pytest.mark.usefixtures("site_context")
def test_process_activate_config(
    config_task_factory: ConfigTaskFactory,
    relays_repository: RelaysRepository,
    tasks_repository: TasksRepository,
    test_user: InternalAuth,
    site_context: Config,
) -> None:
    # arrange

    # Register two relays
    relay_id_1 = relays_repository.add_relay(test_user, alias="test-relay-1")
    relay_id_2 = relays_repository.add_relay(test_user, alias="test-relay-2")

    cf = create_config_folder(site_context.omd_root, [relay_id_1, relay_id_2])

    config_task_factory.process()

    # assert
    tasks_relay_1_enqueued = tasks_repository.get_tasks(relay_id_1)
    tasks_relay_2_enqueued = tasks_repository.get_tasks(relay_id_2)

    assert len(tasks_relay_1_enqueued) == 1
    assert isinstance(tasks_relay_1_enqueued[0].spec, RelayConfigSpec)
    assert tasks_relay_1_enqueued[0].spec.serial == cf.serial

    assert len(tasks_relay_2_enqueued) == 1
    assert isinstance(tasks_relay_2_enqueued[0].spec, RelayConfigSpec)
    assert tasks_relay_2_enqueued[0].spec.serial == cf.serial

    cf.assert_tar_content(relay_id_1, tasks_relay_1_enqueued[0].spec.tar_data)
    cf.assert_tar_content(relay_id_2, tasks_relay_2_enqueued[0].spec.tar_data)
