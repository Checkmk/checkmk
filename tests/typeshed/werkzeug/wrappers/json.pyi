from typing import Any


class JSONMixin:
    @property
    def is_json(self) -> bool:
        ...

    @property
    def json(self):
        ...

    def get_json(self, force: bool = ..., silent: bool = ..., cache: bool = ...):
        ...

    def on_json_loading_failed(self, e: Any) -> None:
        ...
