/**
 * Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type {
  AllValidationMessages,
  ComponentSpec,
  StageData
} from '@/quick-setup/components/quick-setup/widgets/widget_types'
import type { WizardMode } from '@/quick-setup/components/quick-setup/useWizard'
import type { LogStep } from './components/BackgroundJobLog/useBackgroundJobLog'
import type { Ref } from 'vue'
import type { BackgroundJobLog } from './components/BackgroundJobLog/useBackgroundJobLog'
import type { QuickSetupStageAction } from './components/quick-setup/quick_setup_types'
/**
 * Quick setup application
 */
export interface QuickSetupAppProps {
  /** @property {string} quick_setup_id - The quick setup id */
  quick_setup_id: string

  /** @property {WizardMode} mode - Sets the quick setup in overview or guided mode */
  mode: WizardMode

  /** @property {boolean} toggle_enabled - When true, the toggling between mode via a button is enabled */
  toggle_enabled: boolean

  /** @property {string} object_id - Optional, if editing an existing object created by quick setup */
  object_id: string | null
}

/**
 * Type definition for internal stage storage
 */
export interface QSStageStore {
  title: string
  sub_title?: string | null
  components?: ComponentSpec[]
  recap?: ComponentSpec[]
  user_input: Ref<StageData>
  form_spec_errors?: AllValidationMessages
  errors?: string[]
  actions: QuickSetupStageAction[]
  background_job_log: BackgroundJobLog
}

/**
 * Widget Content for stages
 */
export interface QuickSetupStageWidgetContentProps {
  /** @property {ComponentSpec[]} components - List of widgets to be rendered */
  components: ComponentSpec[]

  /** @property {StageData} userInput - Formspec's data input */
  userInput: StageData

  /** @property {AllValidationMessages} formSpecErrors - Formspec validation errors  */
  formSpecErrors?: AllValidationMessages

  /** @property {LogStep[]} backgroundJobLog - Array of LogStep from the Quick Setup background job log */
  backgroundJobLog?: LogStep[]

  /** @property {boolean} isBackgroundJobRunning - Flag to indicate if a background job is running */
  isBackgroundJobRunning?: boolean
}
