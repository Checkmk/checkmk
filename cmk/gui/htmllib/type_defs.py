from __future__ import annotations

import json
from dataclasses import asdict, dataclass


@dataclass
class RequireConfirmation:
    html: str
    confirmButtonText: str = "Yes"
    cancelButtonText: str = "No"
    customClass = {
        "confirmButton": "confirm_question",
        "icon": "confirm_icon confirm_question",
    }

    def serialize(self) -> str:
        return json.dumps(asdict(self))
