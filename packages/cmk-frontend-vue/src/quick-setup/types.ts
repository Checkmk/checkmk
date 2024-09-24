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

/**
 * Quick setup application
 */
export interface QuickSetupAppProps {
  /** @property {string} quick_setup_id - The quick setup id */
  quick_setup_id: string
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
}
