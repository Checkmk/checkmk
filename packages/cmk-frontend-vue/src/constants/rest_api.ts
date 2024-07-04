const API_ROOT = 'api/1.0'

/** @constant {string} GET_QUICK_SETUP_OVERVIEW_URL - Endpoint used to fecth the quick setup overview and first stage */
export const GET_QUICK_SETUP_OVERVIEW_URL = `${API_ROOT}/objects/quick_setup/{QUICK_SETUP_ID}`

/** @constant {string} VALIDATE_QUICK_SETUP_STEP_URL - Endpoint used to validate stage steps and get the next stage */
export const VALIDATE_QUICK_SETUP_STEP_URL = `${API_ROOT}/domain-types/quick_setup/collections/all`
