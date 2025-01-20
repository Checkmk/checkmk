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
import type { QuickSetupStageRequest } from '@/lib/rest-api-client/quick-setup/request_schemas'
import { AxiosError, type InternalAxiosRequestConfig } from 'axios'

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
    throw processError(error as Error)
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

  let data = undefined
  try {
    data = objectId
      ? await quickSetupClient.editQuickSetup(quickSetupId, buttonId, stages, objectId)
      : await quickSetupClient.runQuickSetupAction(quickSetupId, buttonId, stages)
  } catch (error) {
    throw processError(error as Error)
  }

  /*
      If the action is executed synchronously, the response is a quick_setup domain object
      with the stage recap.

      If the action is executed asynchronously, an object of the background_job domain is returned.
      The result can be obtained after the job has finished executing.
    */
  if ('domainType' in data && data.domainType === 'background_job') {
    await _waitForBackgroundJobToFinish(data.id)
    data = await quickSetupClient.fetchBackgroundJobResult(data.id)

    //It is possible that a 200 response carries error messages. This must raise an arror
    if (data?.background_job_exception || data?.all_stage_errors) {
      throw _createAxiosError(data)
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
    if ('domainType' in data && data.domainType === 'background_job') {
      await _waitForBackgroundJobToFinish(data.id)
      data = await quickSetupClient.fetchStageBackgroundJobResult(data.id)

      //It is possible that a 200 response carries error messages. This must raise an error
      if (data?.background_job_exception || data?.validation_errors) {
        throw _createAxiosError(data)
      }
    }

    return data as QuickSetupStageActionResponse
  } catch (err) {
    throw processError(err as Error)
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

/**
 * This function creates a dummy AxiosError with error information from the background job in order to process it on the error handler
 *
 * @param data response from axios call
 * @returns AxiosError
 */
const _createAxiosError = (data: unknown): AxiosError => {
  const err = new AxiosError(undefined, undefined, undefined, undefined, {
    status: 400,
    data: data,
    statusText: 'Bad Request',
    headers: {},
    config: undefined as unknown as InternalAxiosRequestConfig
  })
  return err
}
