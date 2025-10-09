#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


# <<<hyperv_vm_checkpoints>>>
# checkpoints 2
# checkpoint.name Server25 - (7/18/2025 - 1:43:55 PM)
# checkpoint.path E:\Server25
# checkpoint.created 07/18/2025 13:44:18
# checkpoint.parent
# checkpoint.name Server25 - (10/7/2025 - 11:36:18 AM)
# checkpoint.path E:\Server25
# checkpoint.created 10/07/2025 11:36:47
# checkpoint.parent Server25 - (7/18/2025 - 1:43:55 PM)

import pytest

from cmk.agent_based.v2 import Metric, Result, State
from cmk.plugins.hyperv_cluster.agent_based.hyperv_vm_checkpoints import (
    _parse_checkpoint_ages,
    check_hyperv_vm_checkpoints,
    CheckpointParams,
    hyperv_vm_checkpoints_default_params,
    parse_hyperv_vm_checkpoints,
    Section,
)


def test_parse_empty_string_table() -> None:
    result = parse_hyperv_vm_checkpoints([])
    assert result == {}


def test_parse_valid_checkpoints() -> None:
    string_table = [
        ["checkpoints", "2"],
        ["checkpoint.name", "Server25", "-", "(7/18/2025", "-", "1:43:55", "PM)"],
        ["checkpoint.path", "E:\\Server25"],
        ["checkpoint.created", "07/18/2025", "13:44:18"],
        ["checkpoint.parent"],
        ["checkpoint.name", "Server25", "-", "(10/7/2025", "-", "11:36:18", "AM)"],
        ["checkpoint.path", "E:\\Server25"],
        ["checkpoint.created", "10/07/2025", "11:36:47"],
        ["checkpoint.parent", "Server25", "-", "(7/18/2025", "-", "1:43:55", "PM)"],
    ]

    result = parse_hyperv_vm_checkpoints(string_table)

    expected = {
        "checkpoints": [
            {
                "name": "Server25 - (7/18/2025 - 1:43:55 PM)",
                "path": "E:\\Server25",
                "created": "07/18/2025 13:44:18",
                "parent": "",
            },
            {
                "name": "Server25 - (10/7/2025 - 11:36:18 AM)",
                "path": "E:\\Server25",
                "created": "10/07/2025 11:36:47",
                "parent": "Server25 - (7/18/2025 - 1:43:55 PM)",
            },
        ]
    }

    assert result == expected
    assert len(result["checkpoints"]) == 2


def test_parse_single_checkpoint() -> None:
    string_table = [
        ["checkpoints", "1"],
        ["checkpoint.name", "TestCheckpoint"],
        ["checkpoint.path", "C:\\VMs\\Test"],
        ["checkpoint.created", "01/01/2025", "12:00:00"],
        ["checkpoint.parent", "ParentCheckpoint"],
    ]

    result = parse_hyperv_vm_checkpoints(string_table)

    expected = {
        "checkpoints": [
            {
                "name": "TestCheckpoint",
                "path": "C:\\VMs\\Test",
                "created": "01/01/2025 12:00:00",
                "parent": "ParentCheckpoint",
            }
        ]
    }

    assert result == expected


def test_parse_checkpoint_without_parent() -> None:
    string_table = [
        ["checkpoints", "1"],
        ["checkpoint.name", "RootCheckpoint"],
        ["checkpoint.path", "D:\\VMs\\Root"],
        ["checkpoint.created", "12/31/2024", "23:59:59"],
        ["checkpoint.parent"],
    ]

    result = parse_hyperv_vm_checkpoints(string_table)

    assert result["checkpoints"][0]["parent"] == ""


def test_parse_incomplete_checkpoint() -> None:
    string_table = [
        ["checkpoints", "1"],
        ["checkpoint.name", "IncompleteCheckpoint"],
        ["checkpoint.path", "E:\\VMs\\Incomplete"],
        # Missing created and parent fields
    ]

    result = parse_hyperv_vm_checkpoints(string_table)

    expected = {
        "checkpoints": [
            {
                "name": "IncompleteCheckpoint",
                "path": "E:\\VMs\\Incomplete",
            }
        ]
    }

    assert result == expected
    assert "created" not in result["checkpoints"][0]
    assert "parent" not in result["checkpoints"][0]


def test_parse_with_empty_lines() -> None:
    string_table = [
        ["checkpoints", "1"],
        [],
        ["checkpoint.name", "TestCheckpoint"],
        [],
        ["checkpoint.path", "C:\\Test"],
        ["checkpoint.created", "01/01/2025", "00:00:00"],
        [],
        ["checkpoint.parent"],
    ]

    result = parse_hyperv_vm_checkpoints(string_table)

    assert len(result["checkpoints"]) == 1
    assert result["checkpoints"][0]["name"] == "TestCheckpoint"


def test_parse_multiple_word_names_and_paths() -> None:
    string_table = [
        ["checkpoints", "1"],
        ["checkpoint.name", "My", "Complex", "Checkpoint", "Name", "With", "Spaces"],
        ["checkpoint.path", "C:\\Program", "Files\\Virtual", "Machines\\Test"],
        ["checkpoint.created", "06/15/2025", "14:30:45"],
        ["checkpoint.parent", "Previous", "Checkpoint", "Name"],
    ]

    result = parse_hyperv_vm_checkpoints(string_table)

    expected_name = "My Complex Checkpoint Name With Spaces"
    expected_path = "C:\\Program Files\\Virtual Machines\\Test"
    expected_parent = "Previous Checkpoint Name"

    assert result["checkpoints"][0]["name"] == expected_name
    assert result["checkpoints"][0]["path"] == expected_path
    assert result["checkpoints"][0]["parent"] == expected_parent


def test_parse_unknown_field_ignored() -> None:
    string_table = [
        ["checkpoints", "1"],
        ["checkpoint.name", "TestCheckpoint"],
        ["checkpoint.unknown_field", "SomeValue"],
        ["checkpoint.path", "C:\\Test"],
        ["checkpoint.created", "01/01/2025", "12:00:00"],
        ["checkpoint.parent"],
    ]

    result = parse_hyperv_vm_checkpoints(string_table)

    checkpoint = result["checkpoints"][0]
    assert "unknown_field" not in checkpoint
    assert len(checkpoint) == 4  # name, path, created, parent


def test_parse_real_world_data() -> None:
    string_table = [
        ["checkpoints", "2"],
        ["checkpoint.name", "Server25", "-", "(7/18/2025", "-", "1:43:55", "PM)"],
        ["checkpoint.path", "E:\\Server25"],
        ["checkpoint.created", "07/18/2025", "13:44:18"],
        ["checkpoint.parent"],
        ["checkpoint.name", "Server25", "-", "(10/7/2025", "-", "11:36:18", "AM)"],
        ["checkpoint.path", "E:\\Server25"],
        ["checkpoint.created", "10/07/2025", "11:36:47"],
        ["checkpoint.parent", "Server25", "-", "(7/18/2025", "-", "1:43:55", "PM)"],
    ]

    result = parse_hyperv_vm_checkpoints(string_table)

    assert len(result["checkpoints"]) == 2

    # First checkpoint
    first = result["checkpoints"][0]
    assert first["name"] == "Server25 - (7/18/2025 - 1:43:55 PM)"
    assert first["path"] == "E:\\Server25"
    assert first["created"] == "07/18/2025 13:44:18"
    assert first["parent"] == ""

    # Second checkpoint
    second = result["checkpoints"][1]
    assert second["name"] == "Server25 - (10/7/2025 - 11:36:18 AM)"
    assert second["path"] == "E:\\Server25"
    assert second["created"] == "10/07/2025 11:36:47"
    assert second["parent"] == "Server25 - (7/18/2025 - 1:43:55 PM)"


def test_parse_checkpoints_line_ignored() -> None:
    string_table = [
        ["checkpoints", "999"],  # This number should be ignored
        ["checkpoint.name", "Test"],
        ["checkpoint.path", "C:\\Test"],
        ["checkpoint.created", "01/01/2025", "12:00:00"],
        ["checkpoint.parent"],
    ]

    result = parse_hyperv_vm_checkpoints(string_table)

    assert len(result["checkpoints"]) == 1
    assert result["checkpoints"][0]["name"] == "Test"


def test_parse_multiple_checkpoints_same_name() -> None:
    string_table = [
        ["checkpoints", "2"],
        ["checkpoint.name", "VM", "Checkpoint", "1"],
        ["checkpoint.path", "C:\\VM1"],
        ["checkpoint.created", "01/01/2025", "12:00:00"],
        ["checkpoint.parent"],
        ["checkpoint.name", "VM", "Checkpoint", "2"],
        ["checkpoint.path", "C:\\VM2"],
        ["checkpoint.created", "01/02/2025", "12:00:00"],
        ["checkpoint.parent", "VM", "Checkpoint", "1"],
    ]

    result = parse_hyperv_vm_checkpoints(string_table)

    assert len(result["checkpoints"]) == 2
    assert result["checkpoints"][0]["name"] == "VM Checkpoint 1"
    assert result["checkpoints"][1]["name"] == "VM Checkpoint 2"
    assert result["checkpoints"][1]["parent"] == "VM Checkpoint 1"


def test_parse_checkpoint_ages_empty_list() -> None:
    result = _parse_checkpoint_ages([])
    assert result == []


def test_parse_checkpoint_ages_valid_checkpoints() -> None:
    # Use a fixed recent date that should work reliably
    checkpoints = [
        {
            "name": "Recent Checkpoint",
            "created": "01/01/2020 12:00:00",  # Fixed date in the past
            "path": "C:\\Test",
        }
    ]

    result = _parse_checkpoint_ages(checkpoints)

    assert len(result) == 1
    name, age = result[0]
    assert name == "Recent Checkpoint"
    assert age > 0  # Should be positive (in the past)
    assert isinstance(age, float)


def test_parse_checkpoint_ages_missing_created_field() -> None:
    checkpoints = [
        {
            "name": "No Created Field",
            "path": "C:\\Test",
            # Missing "created" field
        },
        {"name": "Has Created Field", "created": "01/01/2020 12:00:00", "path": "C:\\Test"},
    ]

    result = _parse_checkpoint_ages(checkpoints)

    # Only checkpoint with created field should be included
    assert len(result) == 1
    assert result[0][0] == "Has Created Field"


def test_parse_checkpoint_ages_multiple_date_formats() -> None:
    checkpoints = [
        {
            "name": "US Format",
            "created": "07/18/2020 13:44:18",  # MM/dd/yyyy
            "path": "C:\\Test",
        },
        {
            "name": "European Format",
            "created": "18/07/2020 13:44:18",  # dd/MM/yyyy
            "path": "C:\\Test",
        },
        {
            "name": "ISO Format",
            "created": "2020-07-18 13:44:18",  # yyyy-MM-dd
            "path": "C:\\Test",
        },
        {
            "name": "German Format",
            "created": "18.07.2020 13:44:18",  # dd.MM.yyyy
            "path": "C:\\Test",
        },
        {
            "name": "AM/PM Format",
            "created": "07/18/2020 1:44:18 PM",  # With AM/PM
            "path": "C:\\Test",
        },
    ]

    result = _parse_checkpoint_ages(checkpoints)

    assert len(result) == 5

    # All should have positive ages (dates in the past)
    for name, age in result:
        assert age > 0
        assert name in [
            "US Format",
            "European Format",
            "ISO Format",
            "German Format",
            "AM/PM Format",
        ]


def test_parse_checkpoint_ages_future_dates() -> None:
    checkpoints = [
        {
            "name": "Future Checkpoint",
            "created": "12/31/2030 23:59:59",  # Far future date
            "path": "C:\\Test",
        }
    ]

    result = _parse_checkpoint_ages(checkpoints)

    assert len(result) == 1
    name, age = result[0]
    assert name == "Future Checkpoint"
    assert age < 0  # Negative age for future dates


def test_parse_checkpoint_ages_very_old_dates() -> None:
    checkpoints = [
        {
            "name": "Old Checkpoint",
            "created": "01/01/2000 00:00:00",  # Year 2000
            "path": "C:\\Test",
        }
    ]

    result = _parse_checkpoint_ages(checkpoints)

    assert len(result) == 1
    name, age = result[0]
    assert name == "Old Checkpoint"
    assert age > 0  # Should be positive (in the past)
    # Should be more than 20 years (rough estimate)
    assert age > 20 * 365 * 24 * 3600


def test_parse_checkpoint_ages_mixed_valid_invalid() -> None:
    checkpoints = [
        {"name": "Valid 1", "created": "01/01/2020 12:00:00", "path": "C:\\Test"},
        {"name": "No Created Field", "path": "C:\\Test"},
        {"name": "Invalid Format", "created": "invalid-format", "path": "C:\\Test"},
        {"name": "Valid 2", "created": "06/15/2021 14:30:00", "path": "C:\\Test"},
    ]

    result = _parse_checkpoint_ages(checkpoints)

    # Only valid checkpoints should be included
    assert len(result) == 2
    names = [item[0] for item in result]
    assert "Valid 1" in names
    assert "Valid 2" in names
    assert "No Created Field" not in names
    assert "Invalid Format" not in names


def test_parse_checkpoint_ages_relative_ordering() -> None:
    checkpoints = [
        {
            "name": "Newer Checkpoint",
            "created": "01/01/2022 12:00:00",  # More recent
            "path": "C:\\Test",
        },
        {
            "name": "Older Checkpoint",
            "created": "01/01/2020 12:00:00",  # Less recent
            "path": "C:\\Test",
        },
    ]

    result = _parse_checkpoint_ages(checkpoints)

    assert len(result) == 2

    # Find the ages
    newer_age = None
    older_age = None

    for name, age in result:
        if name == "Newer Checkpoint":
            newer_age = age
        elif name == "Older Checkpoint":
            older_age = age

    assert newer_age is not None
    assert older_age is not None
    assert older_age > newer_age  # Older checkpoint should have larger age


def test_parse_checkpoint_ages_return_type() -> None:
    checkpoints = [{"name": "Type Test", "created": "01/01/2020 12:00:00", "path": "C:\\Test"}]

    result = _parse_checkpoint_ages(checkpoints)

    assert isinstance(result, list)
    assert len(result) == 1

    name, age = result[0]
    assert isinstance(name, str)
    assert isinstance(age, float)


def test_parse_checkpoint_ages_edge_case_dates() -> None:
    checkpoints = [
        {
            "name": "Leap Year",
            "created": "02/29/2020 12:00:00",  # Leap year date
            "path": "C:\\Test",
        },
        {
            "name": "New Year",
            "created": "01/01/2021 00:00:00",  # New year
            "path": "C:\\Test",
        },
        {
            "name": "Year End",
            "created": "12/31/2021 23:59:59",  # Year end
            "path": "C:\\Test",
        },
    ]

    result = _parse_checkpoint_ages(checkpoints)

    assert len(result) == 3

    # All should have valid names and positive ages
    for name, age in result:
        assert name in ["Leap Year", "New Year", "Year End"]
        assert age > 0  # All should be in the past
        assert isinstance(age, float)


def test_parse_checkpoint_ages_multiple_same_dates() -> None:
    same_date = "06/15/2021 12:00:00"
    checkpoints = [
        {"name": "Checkpoint A", "created": same_date, "path": "C:\\TestA"},
        {"name": "Checkpoint B", "created": same_date, "path": "C:\\TestB"},
    ]

    result = _parse_checkpoint_ages(checkpoints)

    assert len(result) == 2

    # Both should have the same age
    age_a = None
    age_b = None

    for name, age in result:
        if name == "Checkpoint A":
            age_a = age
        elif name == "Checkpoint B":
            age_b = age

    assert age_a is not None
    assert age_b is not None
    assert abs(age_a - age_b) < 1  # Should be essentially the same


def test_parse_checkpoint_ages_preserves_names() -> None:
    checkpoints = [
        {
            "name": "Server25 - (Complex Name With Symbols !@#)",
            "created": "01/01/2020 12:00:00",
            "path": "E:\\ComplexPath\\With Spaces",
        }
    ]

    result = _parse_checkpoint_ages(checkpoints)

    assert len(result) == 1
    name, age = result[0]
    assert name == "Server25 - (Complex Name With Symbols !@#)"
    assert age > 0


def test_check_no_checkpoint_data() -> None:
    section: Section = {}
    params = hyperv_vm_checkpoints_default_params

    results = list(check_hyperv_vm_checkpoints(params, section))

    assert len(results) == 1
    assert isinstance(results[0], Result)
    assert results[0].state == State.UNKNOWN
    assert results[0].summary == "No checkpoint data found"


def test_check_empty_checkpoints() -> None:
    section: Section = {"checkpoints": []}
    params = hyperv_vm_checkpoints_default_params

    results = list(check_hyperv_vm_checkpoints(params, section))

    assert len(results) == 1
    assert isinstance(results[0], Result)
    assert results[0].state == State.OK
    assert results[0].summary == "Checkpoints: 0"


def test_check_checkpoints_without_valid_dates() -> None:
    section: Section = {
        "checkpoints": [
            {
                "name": "Checkpoint without date",
                "path": "C:\\Test",
                # Missing "created" field
            },
            {
                "name": "Checkpoint with invalid date",
                "path": "C:\\Test",
                "created": "invalid-date-format",
            },
        ]
    }
    params = hyperv_vm_checkpoints_default_params

    results = list(check_hyperv_vm_checkpoints(params, section))

    assert len(results) == 1
    assert isinstance(results[0], Result)
    assert results[0].state == State.UNKNOWN
    assert results[0].summary == "No valid checkpoint dates found"


def test_check_single_checkpoint() -> None:
    section: Section = {
        "checkpoints": [
            {"name": "Single Checkpoint", "path": "C:\\Test", "created": "01/01/2020 12:00:00"}
        ]
    }
    params = hyperv_vm_checkpoints_default_params

    results = list(check_hyperv_vm_checkpoints(params, section))

    # Should have: count result, newest age check, oldest age check
    assert len(results) >= 3

    # First result should be the count
    count_result = results[0]
    assert isinstance(count_result, Result)
    assert count_result.state == State.OK
    assert count_result.summary == "Checkpoints: 1"

    # Check that we have results for both newest and oldest (same in this case)
    result_objects = [r for r in results[1:] if isinstance(r, Result)]
    labels = [r.summary.split(":")[0] if ":" in r.summary else "" for r in result_objects]
    assert any("Last" in label for label in labels)
    assert any("Oldest" in label for label in labels)


def test_check_multiple_checkpoints() -> None:
    section = {
        "checkpoints": [
            {
                "name": "Newer Checkpoint",
                "path": "C:\\Test",
                "created": "01/01/2022 12:00:00",  # More recent
            },
            {
                "name": "Older Checkpoint",
                "path": "C:\\Test",
                "created": "01/01/2020 12:00:00",  # Less recent
            },
            {
                "name": "Middle Checkpoint",
                "path": "C:\\Test",
                "created": "01/01/2021 12:00:00",  # In between
            },
        ]
    }
    params = hyperv_vm_checkpoints_default_params

    results = list(check_hyperv_vm_checkpoints(params, section))

    assert len(results) >= 3

    count_result = results[0]
    assert isinstance(count_result, Result)
    assert count_result.state == State.OK
    assert count_result.summary == "Checkpoints: 3"


def test_check_with_warning_levels() -> None:
    section: Section = {
        "checkpoints": [
            {
                "name": "Very Old Checkpoint",
                "path": "C:\\Test",
                "created": "01/01/2000 12:00:00",  # Very old
            }
        ]
    }

    # Set strict warning levels (1 day warning, 2 days critical)
    params: CheckpointParams = {
        "age_oldest": ("fixed", (86400.0, 172800.0)),  # 1 day, 2 days
        "age": ("no_levels", None),
    }

    results = list(check_hyperv_vm_checkpoints(params, section))

    # Check that we get some warning/critical state
    states = [r.state for r in results if isinstance(r, Result)]
    assert State.WARN in states or State.CRIT in states


def test_check_with_no_levels() -> None:
    section: Section = {
        "checkpoints": [
            {"name": "Test Checkpoint", "path": "C:\\Test", "created": "01/01/2020 12:00:00"}
        ]
    }

    params: CheckpointParams = {"age_oldest": ("no_levels", None), "age": ("no_levels", None)}

    results = list(check_hyperv_vm_checkpoints(params, section))

    # Should not have any warning/critical states
    states = [r.state for r in results if isinstance(r, Result)]
    assert State.WARN not in states
    assert State.CRIT not in states
    assert State.OK in states


def test_check_newest_vs_oldest() -> None:
    section: Section = {
        "checkpoints": [
            {
                "name": "Checkpoint A",
                "path": "C:\\Test",
                "created": "01/01/2020 12:00:00",  # Oldest
            },
            {
                "name": "Checkpoint B",
                "path": "C:\\Test",
                "created": "01/01/2023 12:00:00",  # Newest
            },
            {
                "name": "Checkpoint C",
                "path": "C:\\Test",
                "created": "01/01/2021 12:00:00",  # Middle
            },
        ]
    }
    params: CheckpointParams = hyperv_vm_checkpoints_default_params

    results = list(check_hyperv_vm_checkpoints(params, section))

    # Find the results with labels
    labeled_results = [r for r in results if isinstance(r, Result) and "(" in r.summary]

    # Should have newest (Checkpoint B) and oldest (Checkpoint A)
    newest_found = any("Checkpoint B" in r.summary for r in labeled_results)
    oldest_found = any("Checkpoint A" in r.summary for r in labeled_results)

    assert newest_found, "Newest checkpoint (Checkpoint B) should be identified"
    assert oldest_found, "Oldest checkpoint (Checkpoint A) should be identified"


def test_check_same_checkpoint_newest_and_oldest() -> None:
    section: Section = {
        "checkpoints": [
            {"name": "Only Checkpoint", "path": "C:\\Test", "created": "01/01/2020 12:00:00"}
        ]
    }
    params: CheckpointParams = hyperv_vm_checkpoints_default_params

    results = list(check_hyperv_vm_checkpoints(params, section))

    # Should have both "Last" and "Oldest" referring to the same checkpoint
    labeled_results = [
        r for r in results if isinstance(r, Result) and "Only Checkpoint" in r.summary
    ]
    assert len(labeled_results) == 2  # One for newest, one for oldest


def test_check_with_future_dates_raises_error() -> None:
    section: Section = {
        "checkpoints": [
            {
                "name": "Future Checkpoint",
                "path": "C:\\Test",
                "created": "12/31/2030 23:59:59",  # Far future
            }
        ]
    }
    params: CheckpointParams = hyperv_vm_checkpoints_default_params

    # Current behavior: Should raise ValueError when trying to render negative timespan
    with pytest.raises(ValueError, match="Cannot render negative timespan"):
        list(check_hyperv_vm_checkpoints(params, section))


def test_check_mixed_valid_invalid_dates() -> None:
    section: Section = {
        "checkpoints": [
            {"name": "Valid Checkpoint 1", "path": "C:\\Test", "created": "01/01/2020 12:00:00"},
            {"name": "Invalid Date Checkpoint", "path": "C:\\Test", "created": "invalid-date"},
            {"name": "Valid Checkpoint 2", "path": "C:\\Test", "created": "01/01/2021 12:00:00"},
            {
                "name": "No Date Checkpoint",
                "path": "C:\\Test",
                # Missing created field
            },
        ]
    }
    params = hyperv_vm_checkpoints_default_params

    results = list(check_hyperv_vm_checkpoints(params, section))

    # Should only count valid checkpoints
    count_result = results[0]
    assert isinstance(count_result, Result)
    assert count_result.state == State.OK
    assert count_result.summary == "Checkpoints: 2"


def test_check_custom_parameters() -> None:
    section: Section = {
        "checkpoints": [
            {"name": "Test Checkpoint", "path": "C:\\Test", "created": "01/01/2020 12:00:00"}
        ]
    }

    custom_params: CheckpointParams = {
        "age_oldest": ("fixed", (1.0, 2.0)),  # Very strict levels
        "age": ("fixed", (3600.0, 7200.0)),  # 1 hour, 2 hours
    }

    results = list(check_hyperv_vm_checkpoints(custom_params, section))

    # Should process without errors
    assert len(results) >= 3

    # Check that all results are Result objects
    result_objects = [r for r in results if isinstance(r, Result)]
    assert len(result_objects) >= 3

    # With such strict levels on very old checkpoint, should trigger critical state
    states = [r.state for r in result_objects]
    assert State.CRIT in states, (
        "Should have critical state due to very strict levels on old checkpoint"
    )

    # First result should be the count (always OK)
    count_result = results[0]
    assert isinstance(count_result, Result)
    assert count_result.state == State.OK
    assert count_result.summary == "Checkpoints: 1"

    # Should have both newest and oldest check results
    check_results = [r for r in result_objects[1:] if ":" in r.summary]
    assert len(check_results) >= 2, "Should have both 'Last' and 'Oldest' check results"

    # At least one should be critical due to strict thresholds
    check_states = [r.state for r in check_results]
    assert State.CRIT in check_states, (
        "At least one check should be critical with strict thresholds"
    )


def test_check_real_world_data() -> None:
    section: Section = {
        "checkpoints": [
            {
                "name": "Server25 - (7/18/2025 - 1:43:55 PM)",
                "path": "E:\\Server25",
                "created": "07/18/2025 13:44:18",
                "parent": "",
            },
            {
                "name": "Server25 - (10/7/2025 - 11:36:18 AM)",
                "path": "E:\\Server25",
                "created": "10/07/2025 11:36:47",
                "parent": "Server25 - (7/18/2025 - 1:43:55 PM)",
            },
        ]
    }
    params: CheckpointParams = hyperv_vm_checkpoints_default_params

    results = list(check_hyperv_vm_checkpoints(params, section))

    # Should process both checkpoints
    count_result = results[0]
    assert isinstance(count_result, Result)
    assert count_result.state == State.OK
    assert count_result.summary == "Checkpoints: 2"

    # Should have both newest and oldest results
    assert len(results) >= 3


def test_check_metrics_present() -> None:
    section: Section = {
        "checkpoints": [
            {"name": "Test Checkpoint", "path": "C:\\Test", "created": "01/01/2020 12:00:00"}
        ]
    }
    params: CheckpointParams = hyperv_vm_checkpoints_default_params

    results = list(check_hyperv_vm_checkpoints(params, section))

    # Look for metric results
    metrics = [r for r in results if isinstance(r, Metric)]
    metric_names = [m.name for m in metrics]

    # Should have metrics for age and age_oldest
    assert "age" in metric_names
    assert "age_oldest" in metric_names


def test_check_label_format() -> None:
    section: Section = {
        "checkpoints": [
            {
                "name": "Complex Checkpoint Name (with symbols)",
                "path": "C:\\Test",
                "created": "01/01/2020 12:00:00",
            }
        ]
    }
    params: CheckpointParams = hyperv_vm_checkpoints_default_params

    results = list(check_hyperv_vm_checkpoints(params, section))

    # Find results with checkpoint names in labels
    labeled_results = [
        r for r in results if isinstance(r, Result) and "Complex Checkpoint Name" in r.summary
    ]

    # Should have both Last and Oldest labels
    assert len(labeled_results) == 2

    last_labels = [r for r in labeled_results if "Last" in r.summary]
    oldest_labels = [r for r in labeled_results if "Oldest" in r.summary]

    assert len(last_labels) == 1
    assert len(oldest_labels) == 1
