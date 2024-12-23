/**
 * Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { processError } from './errors'
import type { StageData } from '../components/quick-setup/widgets/widget_types'

import { wait } from '@/lib/utils'
import type {
  QuickSetupCompleteResponse,
  QuickSetupGuidedResponse,
  QuickSetupOverviewResponse,
  QuickSetupResponse,
  QuickSetupStageActionResponse,
  QuickSetupStageStructure
} from '@/lib/rest-api-client/quick-setup/response_schemas'

import {
  quickSetup as quickSetupClient,
  backgroundJob as backgroundJobClient
} from '@/lib/rest-api-client'
import type { QuickSetupStageRequest } from '@/lib/rest-api-client/quick-setup/request_types'

/** @constant {number} BACKGROUND_JOB_CHECK_INTERVAL - Wait time in milliseconds between checks */
export const BACKGROUND_JOB_CHECK_INTERVAL = 5000

/**
 * Retrive all stages overview together with the first stage components
 * @param quickSetupId string
 * @param objectId string | null
 * @returns Promise<QuickSetupOverviewRestApiResponse>
 */
export const getOverview = async (
  quickSetupId: string,
  objectId: string | null = null
): Promise<QuickSetupGuidedResponse> => {
  return _getOverviewOrAllStages(
    quickSetupId,
    'guided',
    objectId
  ) as Promise<QuickSetupGuidedResponse>
}

/**
 * Retrieve all stages components of a quick setup
 * @param quickSetupId string
 * @param objectId string | null
 * @returns Promise<QuickSetupOverviewResponse>
 */
export const getAllStages = async (
  quickSetupId: string,
  objectId: string | null = null
): Promise<QuickSetupOverviewResponse> => {
  return _getOverviewOrAllStages(
    quickSetupId,
    'overview',
    objectId
  ) as Promise<QuickSetupOverviewResponse>
}

/**
 * Retrive all stages overview together with the first stage components or all stages components of a quick setup
 * @param quickSetupId string
 * @param mode 'guided' | 'overview'
 * @param objectId string
 * @returns Promise<QuickSetupResponse>
 */
const _getOverviewOrAllStages = async (
  quickSetupId: string,
  mode: 'overview' | 'guided',
  objectId: string | null = null
): Promise<QuickSetupResponse> => {
  try {
    return await quickSetupClient.getOverviewModeOrGuidedMode(quickSetupId, mode, objectId)
  } catch (error) {
    throw processError(error)
  }
}

/**
 * Save a new quick setup configuration
 * @param quickSetupId string
 * @param buttonId string
 * @param formData StageData[]
 * @returns Promise<QuickSetupCompleteResponse>
 */
export const saveQuickSetup = async (
  quickSetupId: string,
  buttonId: string,
  formData: StageData[]
): Promise<QuickSetupCompleteResponse> => {
  return _saveOrEditQuickSetup(quickSetupId, buttonId, formData)
}

/**
 * Save an existing quick setup configuration
 * @param quickSetupId string
 * @param buttonId string
 * @param formData StageData[]
 * @param objectId string
 * @returns Promise<QuickSetupCompleteResponse>
 */
export const editQuickSetup = async (
  quickSetupId: string,
  buttonId: string,
  formData: StageData[],
  objectId: string
): Promise<QuickSetupCompleteResponse> => {
  return _saveOrEditQuickSetup(quickSetupId, buttonId, formData, objectId)
}

/**
 * Save a new quick setup configuration or edit an existing one
 * @param quickSetupId string
 * @param buttonId string
 * @param formData StageData[]
 * @param objectId? string
 * @returns Promise<QuickSetupCompleteResponse>
 */
const _saveOrEditQuickSetup = async (
  quickSetupId: string,
  buttonId: string,
  formData: StageData[],
  objectId?: string
): Promise<QuickSetupCompleteResponse> => {
  const stages: QuickSetupStageRequest[] = formData.map((stage) => ({ form_data: stage }))

  let data = objectId
    ? await quickSetupClient.editQuickSetup(quickSetupId, buttonId, stages, objectId)
    : await quickSetupClient.runQuickSetupAction(quickSetupId, buttonId, stages)

  /*
      If the action is executed synchronously, the response is a quick_setup domain object 
      with the stage recap.

      If the action is executed asynchronously, an object of the background_job domain is returned. 
      The result can be obtained after the job has finished executing.
    */
  if ('domain_type' in data && data.domain_type === 'background_job') {
    await _waitForBackgroundJobToFinish(data.job_id)
    data = await quickSetupClient.fetchBackgroundJobResult(data.job_id)

    //It is possible that a 200 response carries error messages. This will raise later a CmkError
    if (data?.background_job_exception) {
      throw data.background_job_exception
    }
  }

  return data as QuickSetupCompleteResponse
}

/**
 * Execute a stage validation action and get the recap
 * @param quickSetupId string
 * @param actionId string
 * @param formData StageData[]
 * @param objectId string | null
 * @returns Promise<QuickSetupActionResponse>
 */
export const validateAndRecapStage = async (
  quickSetupId: string,
  actionId: string,
  formData: StageData[]
): Promise<QuickSetupStageActionResponse> => {
  const stages = formData.map((stage) => ({ form_data: stage }))

  try {
    let data = await quickSetupClient.runStageAction(quickSetupId, actionId, stages)

    /*
      If the action is executed synchronously, the response is a quick_setup domain object 
      with the stage recap.

      If the action is executed asynchronously, an object of the background_job domain is returned. 
      The result can be obtained after the job has finished executing.
    */
    if ('domain_type' in data && data.domain_type === 'background_job') {
      await _waitForBackgroundJobToFinish(data.job_id)
      data = await quickSetupClient.fetchStageBackgroundJobResult(data.job_id)

      //It is possible that a 200 response carries error messages. This will raise later a CmkError
      if (data?.background_job_exception) {
        throw data.background_job_exception
      }
    }

    return data as QuickSetupStageActionResponse
  } catch (err) {
    throw processError(err)
  }
}

/**
 * Retrieve the structure of a stage
 * @param quickSetupId string
 * @param stageIndex number
 * @param objectId string | null
 * @returns
 */
export const getStageStructure = async (
  quickSetupId: string,
  stageIndex: number,
  objectId: string | null = null
): Promise<QuickSetupStageStructure> => {
  return quickSetupClient.getStageStructure(quickSetupId, stageIndex, objectId)
}

/**
 * Wait until background job is finished
 * @param id string - Background Job ID
 */
const _waitForBackgroundJobToFinish = async (id: string): Promise<void> => {
  let isActive = true
  do {
    const data = await backgroundJobClient.get(id)
    isActive = !!data.extensions.active

    if (!isActive) {
      return
    }

    await wait(BACKGROUND_JOB_CHECK_INTERVAL)
  } while (isActive)
}
