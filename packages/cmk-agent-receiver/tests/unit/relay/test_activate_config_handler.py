import pytest

from cmk.agent_receiver.relay.api.routers.tasks.handlers.activate_config import (
    ActivateConfigHandler,
)
from cmk.agent_receiver.relay.api.routers.tasks.libs.tasks_repository import (
    RelayConfigSpec,
    TasksRepository,
)
from cmk.agent_receiver.relay.lib.relays_repository import RelaysRepository
from cmk.agent_receiver.relay.lib.site_auth import InternalAuth


@pytest.mark.usefixtures("site_context")
def test_process_activate_config(
    activate_config_handler: ActivateConfigHandler,
    relays_repository: RelaysRepository,
    tasks_repository: TasksRepository,
    test_user: InternalAuth,
) -> None:
    # arrange

    # Register two relays
    relay_id_1 = relays_repository.add_relay(test_user, alias="test-relay-1")
    relay_id_2 = relays_repository.add_relay(test_user, alias="test-relay-2")

    # act
    activate_config_handler.process()

    # assert
    tasks_relay_1_enqueued = tasks_repository.get_tasks(relay_id_1)
    tasks_relay_2_enqueued = tasks_repository.get_tasks(relay_id_2)

    assert len(tasks_relay_1_enqueued) == 1
    assert isinstance(tasks_relay_1_enqueued[0].spec, RelayConfigSpec)
    assert tasks_relay_1_enqueued[0].spec.tar_data == ""

    assert len(tasks_relay_2_enqueued) == 1
    assert isinstance(tasks_relay_2_enqueued[0].spec, RelayConfigSpec)
    assert tasks_relay_2_enqueued[0].spec.tar_data == ""
