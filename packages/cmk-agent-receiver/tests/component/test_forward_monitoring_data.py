import base64
import uuid
from http import HTTPStatus
from time import time
from unittest.mock import patch

from cmk.agent_receiver.config import Config
from cmk.relay_protocols.monitoring_data import MonitoringData
from cmk.relay_protocols.relays import RelayRegistrationResponse
from cmk.testlib.agent_receiver.agent_receiver import AgentReceiverClient
from cmk.testlib.agent_receiver.config_file_system import create_config_folder
from cmk.testlib.agent_receiver.mock_socket import create_socket
from cmk.testlib.agent_receiver.site_mock import OP, SiteMock


def register_relay(ar: AgentReceiverClient, name: str) -> str:
    resp = ar.register_relay(name)
    parsed = RelayRegistrationResponse.model_validate_json(resp.text)
    return parsed.relay_id


def test_forward_monitoring_data(
    agent_receiver: AgentReceiverClient,
    site: SiteMock,
    site_context: Config,
) -> None:
    relay_name = str(uuid.uuid4())
    host = "testhost"
    site.set_scenario([], [(relay_name, OP.ADD)])
    relay_id = register_relay(agent_receiver, relay_name)
    cf = create_config_folder(root=site_context.omd_root, relays=[relay_id])
    agent_receiver.set_serial(cf.serial)

    payload = b"monitoring payload"
    timestamp = int(time())
    expected_header = (
        f"payload_type:fetcher;"
        f"payload_size:{len(payload)};"
        f"config_serial:{cf.serial};"
        f"start_timestamp:{timestamp};"
        f"host_by_name:{host};"
    )
    with create_socket() as ms:
        with patch.object(Config, "raw_data_socket", ms.socket_path):
            monitoring_data = MonitoringData(
                serial=cf.serial,
                host=host,
                timestamp=timestamp,
                payload=base64.b64encode(payload),
            )
            response = agent_receiver.forward_monitoring_data(
                relay_id=relay_id,
                monitoring_data=monitoring_data,
            )
            assert response.status_code == HTTPStatus.OK, response.text
            received = ms.data_queue.get(timeout=5.0)
            lines = received.splitlines()
            assert lines[0].decode() == expected_header
            assert lines[1] == payload
