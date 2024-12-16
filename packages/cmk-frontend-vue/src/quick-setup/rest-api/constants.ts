/**
 * Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
const API_ROOT = 'api/1.0'

/** @constant {string} GET_QUICK_SETUP_OVERVIEW_URL - Endpoint used to fetch the quick setup overview and first stage */
export const GET_QUICK_SETUP_OVERVIEW_URL = `${API_ROOT}/objects/quick_setup/{QUICK_SETUP_ID}`

/** @constant {string} GET_QUICK_SETUP_STAGE_ACTION_JOB_RESULT_URL - Fetch the Quick setup stage action background job result
 */
export const GET_QUICK_SETUP_STAGE_ACTION_JOB_RESULT_URL = `${API_ROOT}/objects/quick_setup_stage_action_result/{JOB_ID}`

/** @constant {string} VALIDATE_QUICK_SETUP_STAGE_URL - Endpoint used to validate a stage and get the next stage */
export const VALIDATE_QUICK_SETUP_STAGE_URL = `${API_ROOT}/domain-types/quick_setup/collections/all`

/** @constant {string}  SAVE_QUICK_SETUP_URL - Save all user input and create a new object via the quick setup */
export const SAVE_QUICK_SETUP_URL = `${API_ROOT}/objects/quick_setup/{QUICK_SETUP_ID}/actions/save/invoke`

/** @constant {string}  EDIT_QUICK_SETUP_URL - Save all user input and edit an existing object created by the quick setup */
export const EDIT_QUICK_SETUP_URL = `${API_ROOT}/objects/quick_setup/{QUICK_SETUP_ID}/actions/edit/invoke`
