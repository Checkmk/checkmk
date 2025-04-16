/**
 * Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { Ref, VNode } from 'vue'
import type { WizardMode } from './useWizard'

export interface QuickSetupStageActionIcon {
  name?: string | undefined
  rotate?: number | undefined
}

export interface QuickSetupStageAction {
  label: string
  ariaLabel?: string | null
  waitLabel: string
  variant: string
  icon: QuickSetupStageActionIcon
  action: () => void
}

export interface QuickSetupProps {
  /** @property {boolean} loading - when true, it hides the current stage's buttons */
  loading: boolean

  /** @property {boolean} currentStage - Currently selected stage */
  currentStage: number

  /** @property {QuickSetupStageSpec[]} regularStages - List of stages */
  regularStages: QuickSetupStageSpec[]

  /** @property {QuickSetupSaveStageSpec} saveStage - This is the last stage, displayed without title, subtitle, or stage number */
  saveStage?: QuickSetupSaveStageSpec | null

  /** @property {WizardMode} mode - Sets the quick setup in overview or guided mode */
  mode: Ref<WizardMode>

  /** @property {boolean} prevent-leaving - this and that */
  preventLeaving: boolean

  /** @property {boolean} hideWaitIcon - When set to true will hide the spinner and "please wait" legend  */
  hideWaitIcon?: boolean
}

/**
 * Specs for stages properties
 */

export interface QuickSetupSaveStageSpec {
  /** @property {VNode | null} content - Component to be displayed as last stage content */
  content?: VnodeOrNull

  /** @property {(string | DetailedError)[]} errors - List of errors (General + stage validation) */
  errors: Readonly<Array<string | DetailedError>>

  /** @property {QuickSetupStageAction[]} actions - List of actions from wich will render buttons */
  actions: Readonly<QuickSetupStageAction[]>
}

export interface QuickSetupStageSpec extends QuickSetupSaveStageSpec {
  /** @property {string} title - Title of the stage */
  title: string

  /** @property {undefined | null | () => void} goToThisStage - Method to open the stage */
  goToThisStage?: (() => void) | null

  /** @property {string | null | undefined} sub_title - Subtitle of the stage */
  sub_title?: string | null

  /** @property {VNode | null | undefined} recapContent - Component to be displayed when the stage is completed */
  recapContent?: VnodeOrNull
}

/**
 * Stage and Save Stage properties
 */
interface QuickSetupSaveAndStageContentProps extends QuickSetupSaveStageSpec {
  /** @property {number} index - Stage index  */
  index: number

  /** @property {number} numberOfStages - How many stages are in total */
  numberOfStages: number

  /** @property {boolean} loading - When true, the buttons of the stage are hidden */
  loading: boolean

  /** @property {WizardMode} mode - Sets the quick setup in overview or guided mode */
  mode: WizardMode

  /** @property {boolean} hideWaitIcon - When set to true will hide the spinner and "please wait" legend  */
  hideWaitIcon?: boolean
}

export interface QuickSetupSaveStageProps extends QuickSetupSaveAndStageContentProps {
  /** @property {number} currentStage - Currently selected stage */
  currentStage: number
}

export interface QuickSetupStageProps extends QuickSetupStageSpec, QuickSetupSaveStageProps {}

export interface QuickSetupStageContent extends QuickSetupSaveAndStageContentProps {
  /** @property {VNode | null} content - Element to be rendered as stage's content */
  content: VnodeOrNull

  /** @property {WizardMode} mode - Sets the quick setup in overview or guided mode */
  mode: WizardMode
}

export type VnodeOrNull = Readonly<VNode> | null

export interface DetailedError {
  type: 'DetailedError'
  message: string
  details: string
}

export const isDetailedError = (value: unknown): value is DetailedError => {
  return (
    typeof value === 'object' && value !== null && 'type' in value && value.type === 'DetailedError'
  )
}
