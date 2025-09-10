/**
 * Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { components } from '@/lib/rest-api-client/openapi_internal'

export type ConfiguredValues = Record<string, string | null>
export type ConfiguredFilters = Record<string, ConfiguredValues>

export type CheckboxConfig = components['schemas']['CheckboxComponentModel']
export type CheckboxGroupConfig = components['schemas']['CheckboxGroupComponentModel']
export type DualListConfig = components['schemas']['DualListComponentModel']
export type DropdownConfig = components['schemas']['DropdownComponentModel']
export type DynamicDropdownConfig = components['schemas']['DynamicDropdownComponentModel']
export type HiddenConfig = components['schemas']['HiddenComponentModel']
export type HorizontalGroupConfig = components['schemas']['HorizontalGroupComponentModel']
export type LabelQueryBuilderConfig = components['schemas']['LabelGroupFilterComponentModel']
export type RadioButtonConfig = components['schemas']['RadioButtonComponentModel']
export type SliderConfig = components['schemas']['SliderComponentModel']
export type StaticTextConfig = components['schemas']['StaticTextComponentModel']
export type TagFilterConfig = components['schemas']['TagFilterComponentModel']
export type TextInputConfig = components['schemas']['TextInputComponentModel']

export type ComponentConfig =
  | RadioButtonConfig
  | TextInputConfig
  | HiddenConfig
  | CheckboxConfig
  | CheckboxGroupConfig
  | StaticTextConfig
  | DropdownConfig
  | DualListConfig
  | DynamicDropdownConfig
  | LabelQueryBuilderConfig
  | TagFilterConfig
  | SliderConfig
  | HorizontalGroupConfig
