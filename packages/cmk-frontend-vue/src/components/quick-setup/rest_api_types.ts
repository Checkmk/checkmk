import type { ValidationMessages } from '@/lib/validation'
import { type ComponentSpec } from './widgets/widget_types'

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
 * Overview spec
 */
export interface QSOverviewSpec {
  stage_id: number
  title: string
  sub_title: string | null
}

/**
 * Request for stage validation
 */
interface QSStageRequest {
  stage_id: number
  form_data: object
}

/**
 * Request to validate the current stage
 */
export interface QSValidateStagesRequest {
  quick_setup_id: string
  stages: QSStageRequest[]
}

/**
 * Response from the API when validating a stage
 */
export interface QSStageResponse {
  stage_id: number
  next_stage_structure: QSStageStructure
  errors: QsStageValidationError | null
  stage_recap: ComponentSpec[]
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
