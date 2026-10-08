/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { components } from 'cmk-shared-typing/typescript/openapi_internal'

import type {
  HostStateContent,
  HostStatisticsContent,
  InventoryContent,
  ServiceStateContent,
  ServiceStatisticsContent,
  SiteOverviewContent
} from '@/dashboard/components/Wizard/types'

export type LinkedContent =
  | HostStatisticsContent
  | ServiceStatisticsContent
  | HostStateContent
  | ServiceStateContent
  | SiteOverviewContent
  | InventoryContent

export type ContextualLinkOf<C extends LinkedContent> = C['contextual_link']
export type ContextFilterIdOf<C extends LinkedContent> = Extract<
  ContextualLinkOf<C>,
  { type: 'custom' }
>['links'][number]['filters'][number]['filter_id']

export type VisualLocation = components['schemas']['VisualLocation']
export type ConfigurableMode = components['schemas']['ConfigurableLinkMode']
export type ContextualLinkOptions = components['schemas']['ContextualLinkOptions']
