import threading
import uuid
from unittest.mock import Mock

import pytest

from cmk.agent_receiver.relay_backend.lib import relays_repository
from cmk.agent_receiver.relay_backend.lib.relays_repository import RelaysRepository


@pytest.fixture(autouse=True)
def clear_global_relays():
    # Clear the global relays dict before each test
    relays_repository.GLOBAL_RELAYS.clear()


def test_add_relay_and_has_relay():
    repo = RelaysRepository()
    relay_id = uuid.uuid4()
    repo.add_relay(relay_id)
    assert repo.has_relay(relay_id)
    assert relay_id in repo.list_relays()


def test_get_relay_tasks_empty():
    repo = RelaysRepository()
    relay_id = uuid.uuid4()
    repo.add_relay(relay_id)
    assert repo.get_relay_tasks(relay_id) == []


def test_get_relay_tasks_with_tasks():
    repo = RelaysRepository()
    relay_id = uuid.uuid4()
    repo.add_relay(relay_id)
    task = Mock()
    relays_repository.GLOBAL_RELAYS[relay_id].append(task)
    assert repo.get_relay_tasks(relay_id) == [task]


def test_has_relay_false_for_unknown():
    repo = RelaysRepository()
    relay_id = uuid.uuid4()
    assert not repo.has_relay(relay_id)


def test_list_relays_multiple():
    repo = RelaysRepository()
    relay_ids = [uuid.uuid4() for _ in range(3)]
    for rid in relay_ids:
        repo.add_relay(rid)
    listed = repo.list_relays()
    assert set(listed) == set(relay_ids)


def test_concurrent_add_relay():
    repo = RelaysRepository()
    relay_ids = [uuid.uuid4() for _ in range(50)]
    threads = []

    def add_relay(relay_id):
        repo.add_relay(relay_id)

    for rid in relay_ids:
        t = threading.Thread(target=add_relay, args=(rid,))
        threads.append(t)
        t.start()

    for t in threads:
        t.join()

    # After all threads complete, all relays should be present
    listed = repo.list_relays()
    assert set(listed) == set(relay_ids)
    assert len(listed) == 50
