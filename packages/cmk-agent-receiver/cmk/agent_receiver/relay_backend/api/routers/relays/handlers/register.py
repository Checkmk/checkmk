import dataclasses
from uuid import UUID


@dataclasses.dataclass
class RegisterRelayHandler:
    def process(self, relay_id: UUID) -> None:
        pass
