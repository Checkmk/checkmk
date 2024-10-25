/**
 * Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import axios from 'axios'

import {
  type GeneralError,
  type QSInitializationResponse,
  type QSValidateStagesRequest,
  type QSStageResponse,
  type ValidationError,
  type QSResponseComplete,
  type QSRequestComplete,
  type QSAllStagesResponse
} from './rest_api_types'
import type { StageData } from './components/quick-setup/widgets/widget_types'

const API_ROOT = 'api/1.0'

/** @constant {string} GET_QUICK_SETUP_OVERVIEW_URL - Endpoint used to fetch the quick setup overview and first stage */
const GET_QUICK_SETUP_OVERVIEW_URL = `${API_ROOT}/objects/quick_setup/{QUICK_SETUP_ID}`

/** @constant {string} VALIDATE_QUICK_SETUP_STAGE_URL - Endpoint used to validate a stage and get the next stage */
const VALIDATE_QUICK_SETUP_STAGE_URL = `${API_ROOT}/domain-types/quick_setup/collections/all`

/** @constant {string}  SAVE_QUICK_SETUP_URL - Save all user input and create a new object via the quick setup */
const SAVE_QUICK_SETUP_URL = `${API_ROOT}/objects/quick_setup/{QUICK_SETUP_ID}/actions/save/invoke`

/** @constant {string}  EDIT_QUICK_SETUP_URL - Save all user input and edit an existing object created by the quick setup */
const EDIT_QUICK_SETUP_URL = `${API_ROOT}/objects/quick_setup/{QUICK_SETUP_ID}/actions/edit/invoke`

/**
 * Returns a record representation of an error to be shown to the user
 * @param err unknown
 * @returns ValidationError | GeneralError
 */

const processError = (err: unknown): ValidationError | GeneralError => {
  if (!axios.isAxiosError(err)) {
    return { type: 'general', general_error: 'Unknown error has occurred' } as GeneralError
  }

  if (err.response?.status === 400) {
    if (err.response.data?.errors) {
      return {
        type: 'validation',
        ...(err.response.data?.errors || err.response.data?.detail)
      } as ValidationError
    } else {
      return { type: 'validation', stage_errors: err.response.data?.detail } as ValidationError
    }
  } else {
    return {
      type: 'general',
      general_error: err?.response?.data?.title || err.message
    } as GeneralError
  }
}

/**
 * Get all stages overview together with the first stage components
 * @param quickSetupId string
 * @param objectId string | null
 * @returns Promise<QuickSetupOverviewRestApiResponse>
 */
export const getOverview = async (
  quickSetupId: string,
  objectId: string | null = null
): Promise<QSInitializationResponse> => {
  return new Promise((resolve, reject) => {
    const baseUrl = GET_QUICK_SETUP_OVERVIEW_URL.replace('{QUICK_SETUP_ID}', quickSetupId)
    const url = objectId ? `${baseUrl}?object_id=${objectId}` : baseUrl
    axios
      .get(url)
      .then((response) => {
        resolve(response.data)
      })
      .catch((err) => {
        reject(processError(err))
      })
  })
}

export const getAllStages = async (
  quickSetupId: string,
  objectId: string | null = null
): Promise<QSAllStagesResponse> => {
  return new Promise((resolve, reject) => {
    const baseUrl = `${GET_QUICK_SETUP_OVERVIEW_URL}?mode=overview`.replace(
      '{QUICK_SETUP_ID}',
      quickSetupId
    )
    const url = objectId ? `${baseUrl}&object_id=${objectId}` : baseUrl
    axios
      .get(url)
      .then((response) => {
        resolve(response.data)
      })
      .catch((err) => {
        reject(processError(err))
      })
  })
}

export const validateStage = async (
  quickSetupId: string,
  formData: StageData[],
  objectId: string | null = null
): Promise<QSStageResponse> => {
  return new Promise((resolve, reject) => {
    const url = objectId
      ? `${VALIDATE_QUICK_SETUP_STAGE_URL}?object_id=${objectId}`
      : VALIDATE_QUICK_SETUP_STAGE_URL
    const payload: QSValidateStagesRequest = {
      quick_setup_id: quickSetupId,
      stages: formData.map((stage) => ({ form_data: stage }))
    }

    axios
      .post(url, payload)
      .then((response) => {
        resolve(response.data)
      })
      .catch((err) => {
        reject(processError(err))
      })
  })
}

export const saveQuickSetup = async (
  quickSetupId: string,
  buttonId: string,
  formData: StageData[]
): Promise<QSResponseComplete> => {
  return new Promise((resolve, reject) => {
    const url = SAVE_QUICK_SETUP_URL.replace('{QUICK_SETUP_ID}', quickSetupId)
    const payload: QSRequestComplete = {
      button_id: buttonId,
      stages: formData.map((step) => ({ form_data: step }))
    }

    axios
      .post(url, payload)
      .then((response) => {
        resolve(response.data)
      })
      .catch((err) => {
        reject(processError(err))
      })
  })
}

export const editQuickSetup = async (
  quickSetupId: string,
  buttonId: string,
  objectId: string,
  formData: StageData[]
): Promise<QSResponseComplete> => {
  return new Promise((resolve, reject) => {
    const url = `${EDIT_QUICK_SETUP_URL}?object_id=${objectId}`.replace(
      '{QUICK_SETUP_ID}',
      quickSetupId
    )
    const payload: QSRequestComplete = {
      button_id: buttonId,
      stages: formData.map((step) => ({ form_data: step }))
    }

    axios
      .put(url, payload)
      .then((response) => {
        resolve(response.data)
      })
      .catch((err) => {
        reject(processError(err))
      })
  })
}
