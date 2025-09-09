/**
 * Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { components } from '@/lib/rest-api-client/openapi_internal'

export type WidgetContent = components['schemas']['WidgetContent']
export type WidgetSizeValue = components['schemas']['WidgetSizeValue']
export type WidgetGeneralSettings = components['schemas']['WidgetGeneralSettings']
export type WidgetFilterContext = components['schemas']['WidgetFilterContext']

export interface BaseWidget {
  widget_id: string
  general_settings: WidgetGeneralSettings
  content: WidgetContent
}

type AnnotatedInfoName = components['schemas']['AnnotatedInfoName']

export interface EffectiveWidgetFilterContext extends WidgetFilterContext {
  restricted_to_single: AnnotatedInfoName[]
}

// Specific widget types
export type LinkedViewContent = components['schemas']['LinkedViewContent']
export type StaticTextContent = components['schemas']['StaticTextContent']
