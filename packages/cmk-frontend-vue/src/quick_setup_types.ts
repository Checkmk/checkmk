/**
 * Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */

import { type ComponentSpec } from './components/quick-setup/widgets/widget_types'

export interface QuickSetupAppProperties {
  quick_setup_id: string
}

export interface OverviewSpec {
  id: string
  title: string
  sub_title?: string
}

export interface StageSpec {
  id: number
  components: ComponentSpec[]
}

export interface QuickSetupOverviewRestApiSpec {
  overviews: OverviewSpec[]
  stage: StageSpec
}

export type StepData = Record<string, object>

export interface QuickSetupStageRequest {
  stage_id: number
  form_data: StepData
}
