/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { CustomGraphOptions } from '@/graphing/designer/api'
import type { ApiDataSource } from '@/graphing/designer/types'

/** The graph an embedded custom graph widget holds, in the custom graph API's shape. */
export interface EmbeddedGraphDefinition {
  data_sources: ApiDataSource[]
  graph_options: CustomGraphOptions
}
