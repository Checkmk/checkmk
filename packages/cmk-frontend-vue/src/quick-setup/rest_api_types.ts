/**
 * Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { type ComponentSpec } from './widgets/widget_types'
import type { ValidationMessages } from '@/form'

/**
 * Common stage structure
 */
export interface QSStageStructure {
  components: ComponentSpec[]
  button_label: string
}

/**
 * Response from the API when initializing the quick setup
 */
export interface QSInitializationResponse {
  quick_setup_id: string
  overviews: QSOverviewSpec[]
  stage: {
    stage_id: number
    stage_recap: ComponentSpec[]
    next_stage_structure: QSStageStructure
  }
  button_complete_label: string
}

/**
 * Overview spec (QuickSetupStageOverviewResponse)
 */
export interface QSOverviewSpec {
  title: string
  sub_title: string | null
}

/**
 * Request for stage validation (QuickSetupStageRequest)
 */
interface QSStageRequest {
  form_data: object
}

/**
 * Request to validate the current stage (QuickSetupRequest)
 */
export interface QSValidateStagesRequest {
  quick_setup_id: string
  stages: QSStageRequest[]
}

/**
 * Response from the API when validating a stage (QuickSetupStageResponse)
 */
export interface QSStageResponse {
  stage_recap: ComponentSpec[]
  next_stage_structure: QSStageStructure
  errors: QsStageValidationError | null
}

/**
 * Error types from stage validation
 */
export interface QsStageValidationError {
  formspec_errors: Record<string, ValidationMessages>
  stage_errors: string[]
}

export interface RestApiError {
  type: string
}

export interface ValidationError extends RestApiError, QsStageValidationError {
  type: 'validation'
}
export interface GeneralError extends RestApiError {
  type: 'general'
  general_error: string
}

/**
 * Request to complete the quick setup (QuickSetupFinalSaveRequest)
 */
export interface QSRequestComplete {
  stages: QSStageRequest[]
}

export interface QSResponseComplete {
  redirect_url: string
}
