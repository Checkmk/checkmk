/**
 * Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */

export interface UnifiedSearchResultElement {
  title: string
  html?: string
  url: string
  context: string
}

export interface UnifiedSearchResultByTopic {
  topic: string
  html?: string
  elements: UnifiedSearchResultElement[]
}

export type UnifiedSearchProviderResult = UnifiedSearchResultByTopic[]
