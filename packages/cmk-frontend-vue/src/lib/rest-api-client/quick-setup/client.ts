/**
 * Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
/**
 * Get guided stages or overview stages
 */

import axios, { isAxiosError } from 'axios'
import { API_ROOT } from '../constants'
import {
  QuickSetupCompleteActionValidationResponse,
  QuickSetupStageActionValidationResponse,
  type QuickSetupCompleteResponse,
  type QuickSetupResponse,
  type QuickSetupStageActionResponse,
  type QuickSetupStageStructure
} from './response_schemas'
import type { QuickSetupStageActionRequest, QuickSetupStageRequest } from './request_schemas'
import type { BackgroundJobSpawnResponse } from '../background-job/response_schemas'

import { argumentError } from '../errors'

const API_DOMAIN = 'quick_setup'
const OVERVIEW_MODE = 'overview'

/**
 * Get guided stages or overview stages
 * @param quickSetupId string
 * @param mode string
 * @param objectId string
 * @returns Promise<QuickSetupResponse>
 */
export const getOverviewModeOrGuidedMode = async (
  quickSetupId: string,
  mode: 'overview' | 'guided',
  objectId: string | null = null
): Promise<QuickSetupResponse> => {
  const url = `${API_ROOT}/objects/${API_DOMAIN}/${quickSetupId}`
  const query: Record<string, string> = {}
  if (objectId) {
    query['object_id'] = objectId
  }

  if (mode === OVERVIEW_MODE) {
    query['mode'] = OVERVIEW_MODE
  }

  try {
    const { data } = await axios.get(url, { params: query })
    return data
  } catch (error) {
    throw argumentError(error as Error)
  }
}

/**
 * Get a quick setup stage structure
 * @param quickSetupId string
 * @param stageIndex number
 * @param objectId string | null
 * @returns Promise<QuickSetupStageStructure>
 */
export const getStageStructure = async (
  quickSetupId: string,
  stageIndex: number,
  objectId: string | null = null
): Promise<QuickSetupStageStructure> => {
  const url = `${API_ROOT}/objects/${API_DOMAIN}/${quickSetupId}/quick_setup_stage/${stageIndex}`
  const query: Record<string, string> = objectId ? { object_id: objectId } : {}

  try {
    const { data } = await axios.get(url, { params: query })
    return data
  } catch (error) {
    throw argumentError(error as Error)
  }
}

/**
 * Run a quick setup stage validation and recap action
 * @param quickSetupId string
 * @param actionId string
 * @param stages QuickSetupStageActionRequest[]
 * @param objectId? string | null
 * @returns Promise<QuickSetupStageActionResponse | BackgroundJobSpawnResponse | QuickSetupStageActionValidationResponse>
 */
export const runStageAction = async (
  quickSetupId: string,
  stageActionId: string,
  stages: QuickSetupStageRequest[]
): Promise<
  | QuickSetupStageActionResponse
  | BackgroundJobSpawnResponse
  | QuickSetupStageActionValidationResponse
> => {
  const url = `${API_ROOT}/objects/${API_DOMAIN}/${quickSetupId}/actions/run-stage-action/invoke`

  try {
    const { data } = await axios.post(url, { stage_action_id: stageActionId, stages })
    return data
  } catch (error) {
    if (
      isAxiosError<QuickSetupStageActionResponse, unknown>(error) &&
      error.response?.data?.validation_errors
    ) {
      return new QuickSetupStageActionValidationResponse(error.response.data)
    }
    throw argumentError(error as Error)
  }
}

/**
 * Run a quick setup action
 * @param quickSetupId string
 * @param actionId string
 * @param stages QuickSetupStageRequest[]
 * @returns Promise<QuickSetupCompleteResponse>
 */
export const runQuickSetupAction = async (
  quickSetupId: string,
  actionId: string,
  stages: QuickSetupStageRequest[]
): Promise<QuickSetupCompleteResponse | BackgroundJobSpawnResponse> => {
  const url = `${API_ROOT}/objects/${API_DOMAIN}/${quickSetupId}/actions/run-action/invoke`

  try {
    const { data } = await axios.post(url, { button_id: actionId, stages })
    return data
  } catch (error) {
    throw argumentError(error as Error)
  }
}

/**
 * Edit the quick setup
 * @param quickSetupId string
 * @param actionId string
 * @param stages QuickSetupStageActionRequest[]
 * @param objectId string
 * @returns Promise<QuickSetupCompleteResponse | BackgroundJobSpawnResponse>
 */
export const editQuickSetup = async (
  quickSetupId: string,
  actionId: string,
  stages: QuickSetupStageRequest[],
  objectId: string
): Promise<QuickSetupCompleteResponse | BackgroundJobSpawnResponse> => {
  const url = `${API_ROOT}/objects/${API_DOMAIN}/${quickSetupId}/actions/edit/invoke?object_id=${objectId}`

  try {
    const { data } = await axios.put(url, { button_id: actionId, stages })
    return data
  } catch (error) {
    throw argumentError(error as Error)
  }
}

/**
 * Save the quick setup
 * @param quickSetupId string
 * @param actionId string
 * @param stages QuickSetupStageActionRequest[]
 * @returns Promise<QuickSetupCompleteResponse | BackgroundJobSpawnResponse>
 */
export const saveQuickSetup = async (
  quickSetupId: string,
  actionId: string,
  stages: QuickSetupStageActionRequest[]
): Promise<QuickSetupCompleteResponse | BackgroundJobSpawnResponse> => {
  const url = `${API_ROOT}/objects/${API_DOMAIN}/${quickSetupId}/actions/save/invoke`

  try {
    const { data } = await axios.put(url, { button_id: actionId, stages })
    return data
  } catch (error) {
    throw argumentError(error as Error)
  }
}

/**
 * Fetch the quick action background job result
 * @param jobId string
 * @returns Promise<QuickSetupCompleteResponse>
 */
export const fetchBackgroundJobResult = async (
  jobId: string
): Promise<QuickSetupCompleteResponse | QuickSetupCompleteActionValidationResponse> => {
  try {
    const { data } = await axios.get(`${API_ROOT}/objects/${API_DOMAIN}_action_result/${jobId}`)

    if (data?.all_stage_errors || data?.background_job_exception) {
      return new QuickSetupCompleteActionValidationResponse(data)
    }

    return data
  } catch (error) {
    throw argumentError(error as Error)
  }
}

/**
 * Fetch the quick setup stage action background job result
 * @param jobId string
 * @returns Promise<QuickSetupStageActionResponse | QuickSetupStageActionValidationResponse>
 */
export const fetchStageBackgroundJobResult = async (
  jobId: string
): Promise<QuickSetupStageActionResponse | QuickSetupStageActionValidationResponse> => {
  try {
    const { data } = await axios.get(
      `${API_ROOT}/objects/${API_DOMAIN}_stage_action_result/${jobId}`
    )

    if (data?.validation_errors || data?.background_job_exception) {
      return new QuickSetupStageActionValidationResponse(data)
    }

    return data
  } catch (error) {
    throw argumentError(error as Error)
  }
}
