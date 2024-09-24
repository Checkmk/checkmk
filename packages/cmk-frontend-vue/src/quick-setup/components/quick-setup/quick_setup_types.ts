/**
 * Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { ComponentSpec } from './widgets/widget_types'
import type { ValidationMessages } from '@/form'

//Quick setup
export interface QuickSetupSpec {
  /** @property {string} quick_setup_id - The quick setup id  */
  quick_setup_id: string
}

//Quick setup stage
export type StageData = Record<string, object>
type AllValidationMessages = Record<string, ValidationMessages>

export interface QuickSetupStageContentSpec {
  /** @property {ComponentSpec[]} components - List of widgets to render in current stage */
  components?: ComponentSpec[]

  /** @property {unknown} user_input - Input from the user */
  user_input?: unknown

  /** @property {AllValidationMessages} form_spec_errors - Object containing the validation errors of all FormSpecWidgets from current stage*/
  form_spec_errors?: AllValidationMessages

  /** @property {string[] | sttring} stage_errors - List of validation errors from the current stage */
  stage_errors?: string[] | string

  /** @property {string[] | string} other_errors - List of validation errors from the current stage */
  other_errors?: string[] | string
}
export interface QuickSetupStageSpec extends QuickSetupStageContentSpec {
  /** @property {string} title - String to be displayed next to the stage number */
  title: string

  /** @property {string} sub_title - String to be displayed below the title in current stage */
  sub_title?: string | null

  /** @property {string} next_button_label - Label for the "go to the next stage" button */
  next_button_label?: string | null

  /** @property {ComponentSpec[]} recap - List of widgets to render in completed stages*/
  recap?: ComponentSpec[]
}

export interface QuickSetupStageWithIndexSpec {
  /**@property {number} index - The index of the current stage */
  index: number

  /**@property {number} numberOfStages - Total stages count */
  numberOfStages: number

  /**@property {number} selectedStage - The selected stage's index  */
  selectedStage: number

  /** @property {boolean} loading - A flag to indicate if the quick-setup is performing a request */
  loading: boolean

  /** @property {QuickSetupStageSpec} spec - Components, titles, subtitles, text, error messages, data, etc of current stage */
  spec: QuickSetupStageSpec

  /** @property {string[] | string} other_errors - Data of the current stage */
  other_errors?: string[] | string

  /** @property {string} next_button_label - Label for the "save" button */
  save_button_label: string
}
