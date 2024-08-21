const API_ROOT = 'api/1.0'

/** @constant {string} GET_QUICK_SETUP_OVERVIEW_URL - Endpoint used to fetch the quick setup overview and first stage */
export const GET_QUICK_SETUP_OVERVIEW_URL = `${API_ROOT}/objects/quick_setup/{QUICK_SETUP_ID}`

/** @constant {string} VALIDATE_QUICK_SETUP_STAGE_URL - Endpoint used to validate a stage and get the next stage */
export const VALIDATE_QUICK_SETUP_STAGE_URL = `${API_ROOT}/domain-types/quick_setup/collections/all`

/** @constant {string}  COMPLETE_QUICK_SETUP_URL - Save all user input and complete the quick setup */
export const COMPLETE_QUICK_SETUP_URL = `${API_ROOT}/objects/quick_setup/{QUICK_SETUP_ID}/actions/save/invoke`
