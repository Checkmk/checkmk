/**
 * Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */

import type { ConfigEntityType } from 'cmk-shared-typing/typescript/configuration_entity'

export interface CreateConfigurationEntity {
  entity_type: ConfigEntityType
  entity_type_specifier: string
  data: object
}

export interface UpdateConfigurationEntity {
  entity_type: ConfigEntityType
  entity_type_specifier: string
  entity_id: string
  data: object
}
