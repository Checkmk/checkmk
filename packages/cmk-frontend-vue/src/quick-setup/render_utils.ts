/**
 * Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { h, markRaw } from 'vue'
import CompositeWidget from '@/quick-setup/components/quick-setup/widgets/CompositeWidget.vue'
import QuickSetupStageWidgetContent from './QuickSetupStageWidgetContent.vue'
import type {
  AllValidationMessages,
  ComponentSpec,
  StageData
} from '@/quick-setup/components/quick-setup/widgets/widget_types'
import type { QuickSetupStageAction, VnodeOrNull } from './components/quick-setup/quick_setup_types'
import type { Action } from '@/lib/rest-api-client/quick-setup/response_schemas'
import type { LogStep } from './components/BackgroundJobLog/useBackgroundJobLog'

export type UpdateCallback = (value: StageData) => void

/**
 * Renders a component for the recap section of a completed stage
 * @param {ComponentSpec[]} recap - List of widgets to render in completed stages
 * @returns VNode | null
 */
export const renderRecap = (recap: ComponentSpec[]): VnodeOrNull => {
  if (!recap || recap.length === 0) {
    return null
  }
  return markRaw(h(CompositeWidget, { items: recap }))
}

/**
 * Renders a component for the content section of an active stage
 * @param {ComponentSpec[]} components - List of widgets to render in current stage
 * @param {UpdateCallback} onUpdate - Callback to update the stage data. It receives the whole stage data
 * @param {LogStep[]} bagckgroundJobLog - Array of strings from the Quick Setup background job log
 * @param {AllValidationMessages} formSpecErrors - Formspec Validation Errors
 * @param {StageData} userInput - The data entered previously by the user
 * @returns
 */
export const renderContent = (
  components: ComponentSpec[],
  onUpdate: UpdateCallback,
  bagckgroundJobLog: LogStep[],
  isBackgroundJobRunning: boolean,
  formSpecErrors?: AllValidationMessages,
  userInput?: StageData
): VnodeOrNull => {
  return markRaw(
    h(QuickSetupStageWidgetContent, {
      components,
      formSpecErrors: formSpecErrors || {},
      userInput: userInput || {},
      onUpdate: onUpdate,
      backgroundJobLog: bagckgroundJobLog,
      isBackgroundJobRunning: isBackgroundJobRunning
    })
  )
}

export enum ActionType {
  Next = 'next',
  Prev = 'prev',
  Save = 'save'
}

type QuickSetupSimpleCallback = () => void
type QuickSetupIdCallback = (id: string) => void
type QuickSetupCallback = QuickSetupSimpleCallback | QuickSetupIdCallback

export const processActionData = (
  actionType: ActionType,
  actionData: Action,
  callback: QuickSetupCallback
): QuickSetupStageAction => {
  const clb: () => void = (
    actionData?.id ? () => callback(actionData.id!) : callback
  ) as QuickSetupSimpleCallback

  return {
    label: actionData.button.label,
    ariaLabel: actionData.button.aria_label || actionData.button.label,
    waitLabel: actionData.load_wait_label,
    variant: actionType,
    icon: {
      name: actionData.button.icon?.name,
      rotate: actionData.button.icon?.rotate
    },
    action: clb
  }
}
