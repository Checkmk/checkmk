/**
 * Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
/**
 * Get guided stages or overview stages
 */

import axios from 'axios'
import { API_ROOT } from '../constants'
import type {
  QuickSetupCompleteResponse,
  QuickSetupResponse,
  QuickSetupStageActionResponse,
  QuickSetupStageStructure
} from './response_schemas'
import type { QuickSetupStageActionRequest, QuickSetupStageRequest } from './request_types'
import type { BackgroundJobSpawnResponse } from '../background-job/response_schemas'

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

  const { data } = await axios.get(url, { params: query })
  return data
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

  const { data } = await axios.get(url, { params: query })
  return data
}

/**
 * Run a quick setup stage validation and recap action
 * @param quickSetupId string
 * @param actionId string
 * @param stages QuickSetupStageActionRequest[]
 * @param objectId? string | null
 * @returns Promise<QuickSetupStageActionResponse | BackgroundJobSpawnResponse>
 */
export const runStageAction = async (
  quickSetupId: string,
  stageActionId: string,
  stages: QuickSetupStageRequest[]
): Promise<QuickSetupStageActionResponse | BackgroundJobSpawnResponse> => {
  const url = `${API_ROOT}/objects/${API_DOMAIN}/${quickSetupId}/actions/run-stage-action/invoke`

  const { data } = await axios.post(url, { stage_action_id: stageActionId, stages })
  return data
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

  const { data } = await axios.post(url, { button_id: actionId, stages })
  return data
}

/**
 * Edit the quick setup
 * @param quickSetupId string
 * @param actionId string
 * @param stages QuickSetupStageActionRequest[]
 * @param objectId string
 * @returns Promise<QuickSetupCompleteResponse>
 */
export const editQuickSetup = async (
  quickSetupId: string,
  actionId: string,
  stages: QuickSetupStageRequest[],
  objectId: string
): Promise<QuickSetupCompleteResponse | BackgroundJobSpawnResponse> => {
  const url = `${API_ROOT}/objects/${API_DOMAIN}/${quickSetupId}/actions/edit/invoke?object_id=${objectId}`

  const { data } = await axios.put(url, { button_id: actionId, stages })
  return data
}

/**
 * Save the quick setup
 * @param quickSetupId string
 * @param actionId string
 * @param stages QuickSetupStageActionRequest[]
 * @returns Promise<QuickSetupCompleteResponse>
 */
export const saveQuickSetup = async (
  quickSetupId: string,
  actionId: string,
  stages: QuickSetupStageActionRequest[]
): Promise<QuickSetupCompleteResponse | BackgroundJobSpawnResponse> => {
  const url = `${API_ROOT}/objects/${API_DOMAIN}/${quickSetupId}/actions/save/invoke`

  const { data } = await axios.put(url, { button_id: actionId, stages })
  return data
}

/**
 * Fetch the quick action background job result
 * @param jobId string
 * @returns Promise<QuickSetupCompleteResponse>
 */
export const fetchBackgroundJobResult = (jobId: string): Promise<QuickSetupCompleteResponse> => {
  const url = `${API_ROOT}/objects/${API_DOMAIN}_action_result/${jobId}`

  return _fetchBackgroundJobResult(url) as Promise<QuickSetupCompleteResponse>
}

/**
 * Fetch the quick setup stage action background job result
 * @param jobId string
 * @returns Promise<QuickSetupStageActionResponse>
 */
export const fetchStageBackgroundJobResult = (
  jobId: string
): Promise<QuickSetupStageActionResponse> => {
  const url = `${API_ROOT}/objects/${API_DOMAIN}_stage_action_result/${jobId}`

  return _fetchBackgroundJobResult(url) as Promise<QuickSetupStageActionResponse>
}

/**
 * Get background job result and check if there is an error
 * @param url string
 * @returns unknown
 * @throws string
 */
const _fetchBackgroundJobResult = async (url: string): Promise<unknown> => {
  const result = await axios.get(url)

  //It is possible that a 200 response carries error messages. This will raise a CmkError
  if (result.data?.background_job_exception) {
    throw result.data.background_job_exception
  }

  return result.data
}
