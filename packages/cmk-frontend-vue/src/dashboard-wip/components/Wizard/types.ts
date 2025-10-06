/**
 * Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { Ref } from 'vue'

import type { components } from '@/lib/rest-api-client/openapi_internal'

import type { SimpleIcons } from '@/components/CmkIcon'

import type {
  EffectiveWidgetFilterContext,
  WidgetGeneralSettings
} from '@/dashboard-wip/types/widget'
import { type QuickSetupStageActionIcon } from '@/quick-setup/components/quick-setup/quick_setup_types'

export interface LabelValueItem {
  label: string
  value: string
}

export interface FilterItem extends LabelValueItem {
  name: string
}

export interface ActionButtonIcon extends QuickSetupStageActionIcon {
  name: SimpleIcons
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

export interface UseWidgetHandler extends UseValidable {
  widgetProps: Ref<WidgetProps>
}
export interface WidgetProps {
  general_settings: WidgetGeneralSettings
  content: WidgetContentType
  effective_filter_context: EffectiveWidgetFilterContext
}

export enum ElementSelection {
  SPECIFIC = 'SINGLE',
  MULTIPLE = 'MULTI'
}

export interface BaseWidgetProp {
  dashboardName: string
}

export type WidgetFiltersType = {
  [key: string]: {
    [key: string]: string
  }
}

export type WidgetContentType =
  | BarplotContent
  | GaugeContent
  | GraphContent
  | TopListContent
  | ScatterplotContent
  | SingleMetricContent
  | HostStateContent
  | HostStateSummaryContent
  | HostStatisticsContent
  | SiteOverviewContent
  | ServiceStateContent
  | ServiceStateSummaryContent
  | ServiceStatisticsContent

export type MetricDisplayRangeModel = components['schemas']['MetricDisplayRangeModel']
export type FixedDataRangeModel = components['schemas']['MetricDisplayRangeFixedModel']
export type BarplotContent = components['schemas']['BarplotContent']
export type GaugeContent = components['schemas']['GaugeContent']
export type GraphContent = components['schemas']['SingleTimeseriesContent']
export type SingleMetricContent = components['schemas']['SingleMetricContent']
export type ScatterplotContent = components['schemas']['AverageScatterplotContent']
export type TopListContent = components['schemas']['TopListContent']
export type HostStateContent = components['schemas']['HostStateContent']
export type HostStateSummaryContent = components['schemas']['HostStateSummaryContent']
export type HostStatisticsContent = components['schemas']['HostStatsContent']
export type SiteOverviewContent = components['schemas']['SiteOverviewContent']
export type ServiceStateContent = components['schemas']['ServiceStateContent']
export type ServiceStateSummaryContent = components['schemas']['ServiceStateSummaryContent']
export type ServiceState = components['schemas']['MonitoringState']
export type ServiceStatisticsContent = components['schemas']['ServiceStatsContent']

export type TitleSpec = components['schemas']['WidgetTitle']
export type DefaultOrColor = components['schemas']['DefaultOrColor']
export type GraphRenderOptions = components['schemas']['GraphRenderOptions']
export type HostState = components['schemas']['HostState']
