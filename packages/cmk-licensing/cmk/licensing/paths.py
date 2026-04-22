#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from pathlib import Path

_LICENSING_DIR = "var/check_mk/licensing"
_INSTANCE_ID_FILE = "etc/omd/instance_id"

_LICENSED_STATE_FILE = f"{_LICENSING_DIR}/licensed_state"
_STATE_FILE_CREATED_FILE = f"{_LICENSING_DIR}/state_file_created"
_STATE_CHANGE_FILE = f"{_LICENSING_DIR}/state_change"
_LICENSE_USAGE_REPORT_FILE = f"{_LICENSING_DIR}/history.json"
_NEXT_RUN_FILE = f"{_LICENSING_DIR}/next_run"
_EXTENSIONS_FILE = f"{_LICENSING_DIR}/extensions.json"

_VERIFICATION_RESPONSE_FILE = f"{_LICENSING_DIR}/verification_response"
_OFFLINE_VERIFICATION_REQUESTS_DIR = f"{_LICENSING_DIR}/offline_verification_requests"
_VERIFICATION_REQUEST_ID_FILE = f"{_LICENSING_DIR}/verification_request_id"
_DISABLE_CHANGES_ACTIVATION_BLOCK_FILE = f"{_LICENSING_DIR}/disable_changes_activation_block"
_VERIFICATION_RESULT_FILE = f"{_LICENSING_DIR}/verification_result.json"
_LICENSE_NOTIFICATION_STATE_FILE = f"{_LICENSING_DIR}/license-notification-state"
_NEXT_ONLINE_VERIFICATION_FILE = f"{_LICENSING_DIR}/next_online_verification"

_LICENSING_SETTINGS_FILE = "etc/check_mk/multisite.d/licensing_settings.mk"
_LICENSING_NOTIFICATION_SETTINGS_FILE = "etc/check_mk/licensing.d/notification_settings.mk"


def get_licensing_dir(omd_root: Path) -> Path:
    return omd_root / _LICENSING_DIR


def get_instance_id_file_path(omd_root: Path) -> Path:
    return omd_root / _INSTANCE_ID_FILE


def get_licensed_state_file_path(omd_root: Path) -> Path:
    return omd_root / _LICENSED_STATE_FILE


def get_state_file_created_file_path(omd_root: Path) -> Path:
    return omd_root / _STATE_FILE_CREATED_FILE


def get_state_change_path(omd_root: Path) -> Path:
    return omd_root / _STATE_CHANGE_FILE


def get_license_usage_report_file_path(omd_root: Path) -> Path:
    return omd_root / _LICENSE_USAGE_REPORT_FILE


def get_next_run_file_path(omd_root: Path) -> Path:
    return omd_root / _NEXT_RUN_FILE


def get_extensions_file_path(omd_root: Path) -> Path:
    return omd_root / _EXTENSIONS_FILE


def get_verification_response_file_path(omd_root: Path) -> Path:
    return omd_root / _VERIFICATION_RESPONSE_FILE


def get_offline_verification_requests_dir(omd_root: Path) -> Path:
    return omd_root / _OFFLINE_VERIFICATION_REQUESTS_DIR


def get_verification_request_id_file_path(omd_root: Path) -> Path:
    return omd_root / _VERIFICATION_REQUEST_ID_FILE


def get_disable_changes_activation_block_file_path(omd_root: Path) -> Path:
    return omd_root / _DISABLE_CHANGES_ACTIVATION_BLOCK_FILE


def get_verification_result_file_path(omd_root: Path) -> Path:
    return omd_root / _VERIFICATION_RESULT_FILE


def get_license_notification_state_file_path(omd_root: Path) -> Path:
    return omd_root / _LICENSE_NOTIFICATION_STATE_FILE


def get_next_online_verification_file_path(omd_root: Path) -> Path:
    return omd_root / _NEXT_ONLINE_VERIFICATION_FILE


def get_licensing_settings_file_path(omd_root: Path) -> Path:
    return omd_root / _LICENSING_SETTINGS_FILE


def get_licensing_notification_settings_file_path(omd_root: Path) -> Path:
    return omd_root / _LICENSING_NOTIFICATION_SETTINGS_FILE
