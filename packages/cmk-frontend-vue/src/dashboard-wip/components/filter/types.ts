/**
 * Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { components } from '@/lib/rest-api-client/openapi_internal'

export type ConfiguredValues = Record<string, string | null>
export type ConfiguredFilters = Record<string, ConfiguredValues>

export type DropdownConfig = components['schemas']['DropdownComponentModel']
export type DynamicDropdownConfig = components['schemas']['DynamicDropdownComponentModel']
export type TextInputConfig = components['schemas']['TextInputComponentModel']
