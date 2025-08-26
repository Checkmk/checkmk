/**
 * Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { Component } from 'vue'
import type { RouteRecordSingleView } from 'vue-router'

export type RRSVMetaFolder = {
  content: unknown
  name: string
  inFolder: string
  type: 'folder'
}
export type RRSVMetaPage = {
  name: string
  inFolder: string
  type: 'page'
}

export interface Route<M extends RRSVMetaFolder | RRSVMetaPage = RRSVMetaFolder | RRSVMetaPage>
  extends RouteRecordSingleView {
  component: Component<{ screenshotMode: boolean }>
  name?: never
  meta: M
}
