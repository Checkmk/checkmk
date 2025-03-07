/**
 * Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */

import type { ValidationMessages } from '@/form'
import { type ComponentSpec } from '@/quick-setup/components/quick-setup/widgets/widget_types'

interface QuickSetupStageOverviewResponse {
  title: string
  sub_title: string | null
}

export interface StageErrors {
  formspec_errors: Record<string, ValidationMessages>
  stage_errors: string[]
}

export interface Errors extends StageErrors {
  stage_index?: number | null
}

interface QuickSetupButton {
  id: string
  label: string
  aria_label?: string | null
}

export interface Action {
  id: string
  button: QuickSetupButton
  load_wait_label: string
}

export interface QuickSetupStageStructure {
  components: ComponentSpec[]
  actions: Action[]
  prev_button?: QuickSetupButton
}

interface BackgroundJobException {
  message: string
  traceback: string
}

export interface QuickSetupStageActionResponse {
  stage_recap: ComponentSpec[]
  validation_errors: Errors
  background_job_exception: BackgroundJobException | null
}

export class QuickSetupStageActionErrorValidationResponse {
  validation_errors: Errors
  background_job_exception: BackgroundJobException | null

  constructor(data: QuickSetupStageActionResponse) {
    this.validation_errors = data.validation_errors
    this.background_job_exception = data.background_job_exception
  }
}

interface QuickSetupCompleteStageResponse {
  title: string
  sub_title?: string | null
  components: ComponentSpec[]
  actions: Action[]
  prev_button?: QuickSetupButton
}

interface QuickSetupBaseResponse {
  quick_setup_id: string
  actions: Action[]
  prev_button?: QuickSetupButton | null
  guided_mode_string: string
  overview_mode_string: string
}

export interface QuickSetupOverviewResponse extends QuickSetupBaseResponse {
  stages: QuickSetupCompleteStageResponse[]
}

export interface QuickSetupGuidedResponse extends QuickSetupBaseResponse {
  overviews: QuickSetupStageOverviewResponse[]
  stage: QuickSetupStageStructure
}

export type QuickSetupResponse = QuickSetupGuidedResponse | QuickSetupOverviewResponse

export interface QuickSetupCompleteResponse {
  redirect_url: string
  all_stage_errors: Errors[]
  background_job_exception: BackgroundJobException | null
}

export class QuickSetupCompleteActionValidationResponse {
  all_stage_errors: Errors[]
  background_job_exception: BackgroundJobException | null

  constructor(data: QuickSetupCompleteResponse) {
    this.all_stage_errors = data.all_stage_errors
    this.background_job_exception = data.background_job_exception
  }
}
