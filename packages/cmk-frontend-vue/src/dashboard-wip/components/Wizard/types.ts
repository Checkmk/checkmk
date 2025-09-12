/**
 * Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { components } from '@/lib/rest-api-client/openapi_internal'

import { type QuickSetupStageActionIcon } from '@/quick-setup/components/quick-setup/quick_setup_types'

export interface LabelValueItem {
  label: string
  value: string
}

export interface FilterItem extends LabelValueItem {
  name: string
}

export interface ActionButtonIcon extends QuickSetupStageActionIcon {
  name: string
  side: 'left' | 'right'
  rotate?: number | undefined
}

export type MetricType = 'single' | 'combined'

export interface HostServiceContext {
  host?: { host: string }
  service?: { service: string }
}

export interface UseValidable {
  validate: () => boolean
}

export enum ElementSelection {
  SPECIFIC = 'SINGLE',
  MULTIPLE = 'MULTI'
}

export type MetricDisplayRangeModel = components['schemas']['MetricDisplayRangeModel']
export type FixedDataRangeModel = components['schemas']['MetricDisplayRangeFixedModel']
export type TitleSpec = components['schemas']['WidgetTitle']
