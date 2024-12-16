/**
 * Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import axios from 'axios'
import { processError } from './errors'
import type { StageData } from '../components/quick-setup/widgets/widget_types'

import {
  BACKGROUND_JOB_CHECK_INTERVAL,
  EDIT_QUICK_SETUP_URL,
  FETCH_BACKGROUND_JOB_RESULT_URL,
  FETCH_QUICK_SETUP_OVERVIEW_URL,
  FETCH_QUICK_SETUP_STAGE_STRUCTURE_URL,
  GET_BACKGROUND_JOB_STATUS_URL,
  SAVE_QUICK_SETUP_URL,
  VALIDATE_AND_RECAP_STAGE_URL
} from './constants'
import type {
  QuickSetupActionResponse,
  QuickSetupCompleteResponse,
  QuickSetupGuidedResponse,
  QuickSetupOverviewResponse,
  QuickSetupStageStructure
} from './response_types'
import type { QuickSetupFinalActionRequest, QuickSetupStageActionRequest } from './request_types'
import { wait } from '@/lib/utils'
/**
 * Wait until background job is finished
 * @param id string - Background Job ID
 */
const waitForBackgroundJobToFinish = async (id: string): Promise<void> => {
  const url = GET_BACKGROUND_JOB_STATUS_URL.replace('{JOB_ID}', id)
  let isActive = true
  do {
    const { data } = await axios.get(url)
    isActive = !!data.extensions.active

    if (!isActive) {
      return
    }

    await wait(BACKGROUND_JOB_CHECK_INTERVAL)
  } while (isActive)
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
): Promise<QuickSetupGuidedResponse> => {
  const baseUrl = FETCH_QUICK_SETUP_OVERVIEW_URL.replace('{QUICK_SETUP_ID}', quickSetupId)
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
): Promise<QuickSetupOverviewResponse> => {
  const baseUrl = `${FETCH_QUICK_SETUP_OVERVIEW_URL}?mode=overview`.replace(
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
): Promise<QuickSetupCompleteResponse> => {
  const url = SAVE_QUICK_SETUP_URL.replace('{QUICK_SETUP_ID}', quickSetupId)
  const payload: QuickSetupFinalActionRequest = {
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
): Promise<QuickSetupCompleteResponse> => {
  const url = `${EDIT_QUICK_SETUP_URL}?object_id=${objectId}`.replace(
    '{QUICK_SETUP_ID}',
    quickSetupId
  )
  const payload: QuickSetupFinalActionRequest = {
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

export const validateAndRecapStage = async (
  quickSetupId: string,
  actionId: string,
  formData: StageData[],
  objectId: string | null = null
): Promise<QuickSetupActionResponse> => {
  const url = (
    objectId
      ? `${VALIDATE_AND_RECAP_STAGE_URL}?object_id=${objectId}`
      : VALIDATE_AND_RECAP_STAGE_URL
  ).replace('{QUICK_SETUP_ID}', quickSetupId)

  const payload: QuickSetupStageActionRequest = {
    stage_action_id: actionId,
    stages: formData.map((stage) => ({ form_data: stage }))
  }

  try {
    let result = await axios.post(url, payload)
    let data = result.data

    /*
      If the action is executed synchronously, the response is a quick_setup domain object 
      with the stage recap.

      If the action is executed asynchronously, an object of the background_job domain is returned. 
      The result can be obtained after the job has finished executing.
    */
    if (data?.domainType === 'background_job') {
      const jobId = data.id
      await waitForBackgroundJobToFinish(jobId)
      const jobResultUrl = FETCH_BACKGROUND_JOB_RESULT_URL.replace('{JOB_ID}', jobId)
      result = await axios.get(jobResultUrl)
      data = result.data
    }

    //TODO: It is possible that a 200 response carries error messages. Should be handled here
    return data
  } catch (err) {
    throw processError(err)
  }
}

export const getStageStructure = async (
  quickSetupId: string,
  stageIndex: number,
  objectId: string | null = null
): Promise<QuickSetupStageStructure> => {
  const url = (
    objectId
      ? `${FETCH_QUICK_SETUP_STAGE_STRUCTURE_URL}?object_id=${objectId}`
      : FETCH_QUICK_SETUP_STAGE_STRUCTURE_URL
  )
    .replace('{QUICK_SETUP_ID}', quickSetupId)
    .replace('{STAGE_INDEX}', stageIndex.toString())

  const { data } = await axios.get(url)
  return data
}
