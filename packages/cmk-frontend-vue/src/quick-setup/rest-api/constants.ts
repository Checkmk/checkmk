/**
 * Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
const API_ROOT = 'api/1.0'

/** @constant {string} FETCH_QUICK_SETUP_STAGE_ACTION_JOB_RESULT_URL - Fetch the Quick setup stage action background job result */
export const FETCH_QUICK_SETUP_STAGE_ACTION_JOB_RESULT_URL = `${API_ROOT}/objects/quick_setup_stage_action_result/{JOB_ID}`

/** @constant {string} FETCH_QUICK_SETUP_OVERVIEW_URL - Get guided stages or overview stages */
export const FETCH_QUICK_SETUP_OVERVIEW_URL = `${API_ROOT}/objects/quick_setup/{QUICK_SETUP_ID}`

/** @constant {string} FETCH_QUICK_SETUP_STAGE_STRUCTURE_URL - Get a Quick setup stage structure*/
export const FETCH_QUICK_SETUP_STAGE_STRUCTURE_URL = `${API_ROOT}/objects/quick_setup/{QUICK_SETUP_ID}/quick_setup_stage/{STAGE_INDEX}`

/** @constant {string} VALIDATE_AND_RECAP_STAGE_URL - Run a quick setup stage validation and recap action */
export const VALIDATE_AND_RECAP_STAGE_URL = `${API_ROOT}/objects/quick_setup/{QUICK_SETUP_ID}/actions/run-stage-action/invoke`

/** @constant {string}  SAVE_QUICK_SETUP_URL - Save the quick setup */
export const SAVE_QUICK_SETUP_URL = `${API_ROOT}/objects/quick_setup/{QUICK_SETUP_ID}/actions/run-action/invoke`

/** @constant {string}  EDIT_QUICK_SETUP_URL - Edit the quick setup */
export const EDIT_QUICK_SETUP_URL = `${API_ROOT}/objects/quick_setup/{QUICK_SETUP_ID}/actions/edit/invoke`

/** @constant {string}  CHECK_BACKGROUND_JOB_STATUS_URL - Get background job status*/
export const GET_BACKGROUND_JOB_STATUS_URL = `${API_ROOT}/objects/background_job/{JOB_ID}`

/** @constant {number} BACKGROUND_JOB_CHECK_INTERVAL - Wait time in milliseconds */
export const BACKGROUND_JOB_CHECK_INTERVAL = 5000

/** @constant {string} FETCH_STAGE_BACKGROUND_JOB_RESULT_URL - Get background job result */
export const FETCH_STAGE_BACKGROUND_JOB_RESULT_URL = `${API_ROOT}/objects/quick_setup_stage_action_result/{JOB_ID}`

/** @constant {string} FETCH_BACKGROUND_JOB_RESULT_URL - Get background job result */
export const FETCH_BACKGROUND_JOB_RESULT_URL = `${API_ROOT}/objects/quick_setup_action_result/{JOB_ID}`
