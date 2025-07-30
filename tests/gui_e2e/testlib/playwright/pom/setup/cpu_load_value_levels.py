#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import logging

from playwright.sync_api import Locator

from tests.gui_e2e.testlib.playwright.pom.page import CmkPage
from tests.gui_e2e.testlib.playwright.pom.setup.predictive_level_helpers import (
    BoundType,
    LevelType,
    PredictionPeriod,
    PREDICTIVE_LEVEL_DEFAULT_HORIZON,
    PredictiveLevelType,
)

logger = logging.getLogger(__name__)


class CPULoadValueLevels:
    """Class for Levels configuration of Value section in Ruleset of 'CPU load (not utilization!)'
    page.
    """

    def __init__(self, page: CmkPage, checkbox_label: str):
        """
        Args:
            base_locator: Base locator of Levels section to search within
            checkbox_label: Text of the top-level checkbox label (e.g., "Levels on CPU load: 1 minute average")
        """
        self.page = page
        self.checkbox_label = checkbox_label

    @property
    def _value_section(self) -> Locator:
        return self.page.main_area.locator(
            f"td[class='dictleft']:has(label:text-is('{self.checkbox_label}'))"
        )

    # === Main Level Control ===
    @property
    def enable_levels_checkbox(self) -> Locator:
        """Main checkbox to enable/disable levels."""
        return self._value_section.locator(
            f"label[for*='levels1_USE']:text('{self.checkbox_label}')"
        )

    @property
    def level_type_dropdown(self) -> Locator:
        """Dropdown to select level type (No Levels, Fixed, Predictive)."""
        return self._value_section.locator("select[name*='levels1_use']")

    # === Fixed Levels Form ===
    @property
    def fixed_levels_form(self) -> Locator:
        """Container for fixed levels configuration."""
        return self._value_section.locator("span[id*='levels1_1_sub']")

    @property
    def fixed_warning_input(self) -> Locator:
        """Input field for fixed warning threshold."""
        return self.fixed_levels_form.locator("input[name*='levels1_1_0']")

    @property
    def fixed_critical_input(self) -> Locator:
        """Input field for fixed critical threshold."""
        return self.fixed_levels_form.locator("input[name*='levels1_1_1']")

    # === Predictive Levels Form ===
    @property
    def predictive_levels_form(self) -> Locator:
        """Container for predictive levels configuration."""
        return self._value_section.locator("span[id*='levels1_2_sub']")

    @property
    def prediction_period_dropdown(self) -> Locator:
        """Dropdown to select prediction period."""
        return self.predictive_levels_form.locator("select[name*='p_period']")

    @property
    def time_horizon_input(self) -> Locator:
        """Input field for time horizon in days."""
        return self.predictive_levels_form.locator("input[name*='p_horizon']")

    # === Upper Bound Dynamic Levels ===
    @property
    def upper_bound_checkbox(self) -> Locator:
        """Checkbox to enable upper bound dynamic levels."""
        return self.predictive_levels_form.locator(
            f"label[for*='levels_upper_USE']:text('{BoundType.DYNAMIC_UPPER}')"
        )

    @property
    def upper_bound_type_dropdown(self) -> Locator:
        """Dropdown for upper bound dynamic levels."""
        return self.predictive_levels_form.locator("select[name*='levels_upper_sel']")

    @property
    def upper_bound_absolute_warning_input(self) -> Locator:
        """Warning input for absolute difference upper bound."""
        return self.predictive_levels_form.locator("input[name*='levels_upper_0_0']")

    @property
    def upper_bound_absolute_critical_input(self) -> Locator:
        """Critical input for absolute difference upper bound."""
        return self.predictive_levels_form.locator("input[name*='levels_upper_0_1']")

    @property
    def upper_bound_relative_warning_input(self) -> Locator:
        """Warning input for relative difference upper bound."""
        return self.predictive_levels_form.locator("input[name*='levels_upper_1_0']")

    @property
    def upper_bound_relative_critical_input(self) -> Locator:
        """Critical input for relative difference upper bound."""
        return self.predictive_levels_form.locator("input[name*='levels_upper_1_1']")

    @property
    def upper_bound_stdev_warning_input(self) -> Locator:
        """Warning input for standard deviation upper bound."""
        return self.predictive_levels_form.locator("input[name*='levels_upper_2_0']")

    @property
    def upper_bound_stdev_critical_input(self) -> Locator:
        """Critical input for standard deviation upper bound."""
        return self.predictive_levels_form.locator("input[name*='levels_upper_2_1']")

    # === Upper Bound Limits ===
    @property
    def upper_bound_limit_checkbox(self) -> Locator:
        """Checkbox to enable upper bound limits."""
        return self.predictive_levels_form.locator(
            f"label[for*='levels_upper_min_USE']:text('{BoundType.LIMIT_DYNAMIC_UPPER}')"
        )

    @property
    def upper_bound_limit_warning_input(self) -> Locator:
        """Input for minimum warning level."""
        return self.predictive_levels_form.locator("input[name*='levels_upper_min_0']")

    @property
    def upper_bound_limit_critical_input(self) -> Locator:
        """Input for minimum critical level."""
        return self.predictive_levels_form.locator("input[name*='levels_upper_min_1']")

    # === Lower Bound Dynamic Levels ===
    @property
    def lower_bound_checkbox(self) -> Locator:
        """Checkbox to enable lower bound dynamic levels."""
        return self.predictive_levels_form.locator(
            f"label[for*='levels_lower_USE']:text('{BoundType.DYNAMIC_LOWER}')"
        )

    @property
    def lower_bound_type_dropdown(self) -> Locator:
        """Dropdown for lower bound calculation type."""
        return self.predictive_levels_form.locator("select[name*='levels_lower_sel']")

    @property
    def lower_bound_absolute_warning_input(self) -> Locator:
        """Warning input for absolute difference lower bound."""
        return self.predictive_levels_form.locator("input[name*='levels_lower_0_0']")

    @property
    def lower_bound_absolute_critical_input(self) -> Locator:
        """Critical input for absolute difference lower bound."""
        return self.predictive_levels_form.locator("input[name*='levels_lower_0_1']")

    @property
    def lower_bound_relative_warning_input(self) -> Locator:
        """Warning input for relative difference lower bound."""
        return self.predictive_levels_form.locator("input[name*='levels_lower_1_0']")

    @property
    def lower_bound_relative_critical_input(self) -> Locator:
        """Critical input for relative difference lower bound."""
        return self.predictive_levels_form.locator("input[name*='levels_lower_1_1']")

    @property
    def lower_bound_stdev_warning_input(self) -> Locator:
        """Warning input for standard deviation lower bound."""
        return self.predictive_levels_form.locator("input[name*='levels_lower_2_0']")

    @property
    def lower_bound_stdev_critical_input(self) -> Locator:
        """Critical input for standard deviation lower bound."""
        return self.predictive_levels_form.locator("input[name*='levels_lower_2_1']")

    # === Action Methods ===

    def enable_levels(self) -> None:
        """Enable levels by checking the main checkbox."""
        logger.info("Enabling levels for: %s", self.checkbox_label)
        self.enable_levels_checkbox.click()
        self.level_type_dropdown.wait_for(state="visible")

    def set_level_type(self, level_type: LevelType) -> None:
        """Set the level type (No Levels, Fixed, or Predictive).

        Args:
            level_type: The type of levels to configure
        """
        logger.info("Setting level type to: %s for %s", level_type.name, self.checkbox_label)
        self.level_type_dropdown.select_option(value=level_type)

    def configure_fixed_levels(self, warning: float, critical: float) -> None:
        """Configure fixed warning and critical thresholds.

        Args:
            warning: Warning threshold value
            critical: Critical threshold value
        """
        logger.info(
            "Configuring fixed levels for %s: warning=%s, critical=%s",
            self.checkbox_label,
            warning,
            critical,
        )
        self.set_level_type(LevelType.FIXED_LEVELS)
        assert self.is_fixed_levels_expanded(), (
            f"Fixed levels form for '{self.checkbox_label}' is not expanded or accessible."
        )
        self.fixed_warning_input.fill(str(warning))
        self.fixed_critical_input.fill(str(critical))

    def configure_predictive_levels(
        self,
        period_text: PredictionPeriod = PredictionPeriod.WEEKLY,
        horizon_days: int = PREDICTIVE_LEVEL_DEFAULT_HORIZON,
    ) -> None:
        """Configure basic predictive levels settings.

        Args:
            period_text: Display text of prediction period
            horizon_days: Time horizon in days
        Raises:
            RuntimeError: If predictive levels form is not properly expanded
        """
        logger.info(
            "Configuring predictive levels for %s: period='%s', horizon=%d days",
            self.checkbox_label,
            period_text,
            horizon_days,
        )

        # Ensure we're in predictive levels mode and the form is expanded
        self.set_level_type(LevelType.PREDICTIVE_LEVELS)
        assert self.is_predictive_levels_expanded(), (
            f"Predictive levels form for '{self.checkbox_label}' is not expanded or accessible."
        )

        # Configure settings
        self.prediction_period_dropdown.select_option(label=period_text)
        self.time_horizon_input.fill(str(horizon_days))

    def configure_upper_bound_levels(
        self, level_type: PredictiveLevelType, warning: float, critical: float
    ) -> None:
        """Configure upper bound predictive levels.

        Args:
            level_type: Type of predictive calculation
            warning: Warning threshold value
            critical: Critical threshold value
        """
        logger.info(
            "Configuring upper bound levels for %s: type=%s, warning=%s, critical=%s",
            self.checkbox_label,
            level_type.name,
            warning,
            critical,
        )

        # Ensure upper bound is enabled
        if not self.upper_bound_checkbox.is_checked():
            self.upper_bound_checkbox.click()

        # Select calculation type
        self.upper_bound_type_dropdown.select_option(label=level_type)

        # Set values based on type
        if level_type == PredictiveLevelType.ABSOLUTE:
            self.upper_bound_absolute_warning_input.fill(str(warning))
            self.upper_bound_absolute_critical_input.fill(str(critical))
        elif level_type == PredictiveLevelType.RELATIVE:
            self.upper_bound_relative_warning_input.fill(str(warning))
            self.upper_bound_relative_critical_input.fill(str(critical))
        elif level_type == PredictiveLevelType.STANDARD_DEVIATION:
            self.upper_bound_stdev_warning_input.fill(str(warning))
            self.upper_bound_stdev_critical_input.fill(str(critical))

    def configure_lower_bound_levels(
        self, level_type: PredictiveLevelType, warning: float, critical: float
    ) -> None:
        """Configure lower bound predictive levels.

        Args:
            level_type: Type of predictive calculation
            warning: Warning threshold value
            critical: Critical threshold value
        """
        logger.info(
            "Configuring lower bound levels for %s: type=%s, warning=%s, critical=%s",
            self.checkbox_label,
            level_type.name,
            warning,
            critical,
        )

        # Ensure lower bound is enabled
        if not self.lower_bound_checkbox.is_checked():
            self.lower_bound_checkbox.click()

        # Select calculation type
        self.lower_bound_type_dropdown.select_option(label=level_type)

        # Set values based on type
        if level_type == PredictiveLevelType.ABSOLUTE:
            self.lower_bound_absolute_warning_input.fill(str(warning))
            self.lower_bound_absolute_critical_input.fill(str(critical))
        elif level_type == PredictiveLevelType.RELATIVE:
            self.lower_bound_relative_warning_input.fill(str(warning))
            self.lower_bound_relative_critical_input.fill(str(critical))
        elif level_type == PredictiveLevelType.STANDARD_DEVIATION:
            self.lower_bound_stdev_warning_input.fill(str(warning))
            self.lower_bound_stdev_critical_input.fill(str(critical))

    def configure_upper_bound_limits(self, warning: float = 0.0, critical: float = 0.0) -> None:
        """Enable and configure upper bound limits.

        Args:
            warning: Minimum warning level
            critical: Minimum critical level
        """
        logger.info(
            "Enabling upper bound limits for %s: warning=%s, critical=%s",
            self.checkbox_label,
            warning,
            critical,
        )
        if not self.upper_bound_limit_checkbox.is_checked():
            self.upper_bound_limit_checkbox.click()
        self.upper_bound_limit_warning_input.fill(str(warning))
        self.upper_bound_limit_critical_input.fill(str(critical))

    # === Status Methods ===
    def is_levels_enabled(self) -> bool:
        """Check if levels are enabled."""
        return self.enable_levels_checkbox.is_checked()

    def get_current_level_type(self) -> str:
        """Get the currently selected level type."""
        return self.level_type_dropdown.input_value()

    def is_upper_bound_enabled(self) -> bool:
        """Check if upper bound dynamic levels are enabled."""
        return self.upper_bound_checkbox.is_checked()

    def is_lower_bound_enabled(self) -> bool:
        """Check if lower bound dynamic levels are enabled."""
        return self.lower_bound_checkbox.is_checked()

    def is_upper_bound_limits_enabled(self) -> bool:
        """Check if upper bound limits are enabled."""
        return self.upper_bound_limit_checkbox.is_checked()

    def is_predictive_levels_expanded(self) -> bool:
        """Check if the predictive levels form is expanded and ready for configuration."""
        try:
            return (
                self.is_levels_enabled()
                and list(LevelType)[int(self.get_current_level_type())]
                == LevelType.PREDICTIVE_LEVELS
                and self.predictive_levels_form.is_visible()
                and self.prediction_period_dropdown.is_visible()
            )
        except Exception:
            return False

    def is_fixed_levels_expanded(self) -> bool:
        """Check if fixed levels are expanded."""
        return (
            self.is_levels_enabled()
            and list(LevelType)[int(self.get_current_level_type())] == LevelType.FIXED_LEVELS
            and self.fixed_levels_form.is_visible()
            and self.fixed_warning_input.is_visible()
            and self.fixed_critical_input.is_visible()
        )

    def is_no_levels_selected(self) -> bool:
        """Check if no levels are selected."""
        return (
            self.is_levels_enabled()
            and list(LevelType)[int(self.get_current_level_type())] == LevelType.NO_LEVELS
        )
