from logging import Logger
from typing import Callable, Collection

from cmk.utils.automation_config import RemoteAutomationConfig


class LicenseDistributionRegistry:
    def __init__(self) -> None:
        self.distribution_function: (
            Callable[[Logger, Collection[RemoteAutomationConfig]], None] | None
        ) = None

    def register(
        self, distribution_function: Callable[[Logger, Collection[RemoteAutomationConfig]], None]
    ) -> None:
        self.distribution_function = distribution_function


license_distribution_registry = LicenseDistributionRegistry()


def distribute_license_to_remotes(
    logger: Logger, remote_automation_configs: Collection[RemoteAutomationConfig]
) -> None:
    if license_distribution_registry.distribution_function is not None:
        license_distribution_registry.distribution_function(logger, remote_automation_configs)
