/**
 * Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import axios from 'axios'
import { processError } from './errors'
import type { StageData } from '../components/quick-setup/widgets/widget_types'
import type {
  QSInitializationResponse,
  QSValidateStagesRequest,
  QSStageResponse,
  QSResponseComplete,
  QSRequestComplete,
  QSAllStagesResponse
} from './types'

import {
  EDIT_QUICK_SETUP_URL,
  GET_QUICK_SETUP_OVERVIEW_URL,
  SAVE_QUICK_SETUP_URL,
  VALIDATE_QUICK_SETUP_STAGE_URL
} from './constants'

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
  const baseUrl = GET_QUICK_SETUP_OVERVIEW_URL.replace('{QUICK_SETUP_ID}', quickSetupId)
  const url = objectId ? `${baseUrl}?object_id=${objectId}` : baseUrl

  try {
    const { data } = await axios.get(url)
    return data
  } catch (error) {
    throw processError(error)
  }
}

export const getAllStages = async (
  quickSetupId: string,
  objectId: string | null = null
): Promise<QSAllStagesResponse> => {
  const baseUrl = `${GET_QUICK_SETUP_OVERVIEW_URL}?mode=overview`.replace(
    '{QUICK_SETUP_ID}',
    quickSetupId
  )
  const url = objectId ? `${baseUrl}&object_id=${objectId}` : baseUrl

  try {
    const { data } = await axios.get(url)
    return data
  } catch (err) {
    throw processError(err)
  }
}

export const validateStage = async (
  quickSetupId: string,
  formData: StageData[],
  //nextStageIndex: number,
  actionId: string | null = null,
  objectId: string | null = null
): Promise<QSStageResponse> => {
  const url = objectId
    ? `${VALIDATE_QUICK_SETUP_STAGE_URL}?object_id=${objectId}`
    : VALIDATE_QUICK_SETUP_STAGE_URL
  const payload: QSValidateStagesRequest = {
    quick_setup_id: quickSetupId,
    stages: formData.map((stage) => ({ form_data: stage }))
  }
  if (actionId) {
    payload.stage_action_id = actionId
  }

  try {
    const { data } = await axios.post(url, payload)
    return data
  } catch (err) {
    throw processError(err)
  }
}

/**
 * Save a new quick setup configuration
 * @param quickSetupId string
 * @param buttonId string
 * @param formData StageData[]
 * @returns
 */
export const saveQuickSetup = async (
  quickSetupId: string,
  buttonId: string,
  formData: StageData[]
): Promise<QSResponseComplete> => {
  const url = SAVE_QUICK_SETUP_URL.replace('{QUICK_SETUP_ID}', quickSetupId)
  const payload: QSRequestComplete = {
    button_id: buttonId,
    stages: formData.map((step) => ({ form_data: step }))
  }

  try {
    const { data } = await axios.post(url, payload)
    return data
  } catch (err) {
    throw processError(err)
  }
}

/**
 * Save an existing quick setup configuration
 * @param quickSetupId string
 * @param buttonId string
 * @param objectId string
 * @param formData StageData[]
 * @returns
 */
export const editQuickSetup = async (
  quickSetupId: string,
  buttonId: string,
  objectId: string,
  formData: StageData[]
): Promise<QSResponseComplete> => {
  const url = `${EDIT_QUICK_SETUP_URL}?object_id=${objectId}`.replace(
    '{QUICK_SETUP_ID}',
    quickSetupId
  )
  const payload: QSRequestComplete = {
    button_id: buttonId,
    stages: formData.map((step) => ({ form_data: step }))
  }

  try {
    const { data } = await axios.put(url, payload)
    return data
  } catch (err) {
    throw processError(err)
  }
}
