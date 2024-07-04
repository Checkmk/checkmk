import type { ValidationMessages } from '@/lib/validation'
import { type ComponentSpec } from './widgets/widget_types'

/**
 * Stage spec
 */
export interface QSStageSpec {
  stage_id: number
  components: ComponentSpec[]
  button_txt: string | null
}

/**
 * Overview
 */
export interface QSOverviewSpec {
  stage_id: number
  title: string
  sub_title?: string | null
}

/**
 * API response when initializing the Quick Setup
 */
export interface QSInitializationResponse {
  quick_setup_id: string
  overviews: QSOverviewSpec[]
  stage: QSStageSpec
  button_complete_label: string
}

/**
 * Stage data to validate
 */
interface QSStageRequest {
  stage_id: number
  form_data: object
}

/**
 * API request to validate data from stage 0..x
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

export interface QSValidateStagesRequest {
  quick_setup_id: string
  stages: QSStageRequest[]
}

export interface QSValidateStagesResponse {
  stage_id: number
  components: ComponentSpec[]
  errors: QsStageValidationError | null
  stage_summary: unknown
  stage_recap: ComponentSpec[]
  button_txt: string
}
