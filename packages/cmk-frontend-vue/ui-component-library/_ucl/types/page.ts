/**
 * Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { Component } from 'vue'

export function toSlug(name: string): string {
  return name
    .trim()
    .toLowerCase()
    .replace(/\s+/g, '-')
    .replace(/[^a-z0-9-]/g, '')
    .replace(/-+/g, '-')
    .replace(/^-|-$/g, '')
}

export type PageStatus = 'new' | 'updated' | 'deprecated'

export type PageOptions =
  | { status?: undefined; statusSince?: undefined }
  | { status: 'new' | 'updated'; statusSince: string }
  | { status: 'deprecated'; statusSince?: undefined }

export class Page {
  name: string
  component: Component<{ screenshotMode: boolean }>
  status?: PageStatus | undefined
  statusSince?: string | undefined

  constructor(
    name: string,
    component: Component<{ screenshotMode: boolean }>,
    options: PageOptions = {}
  ) {
    this.name = name
    this.component = component
    this.status = options.status
    this.statusSince = options.statusSince
  }
}

export class Folder {
  name: string
  pages: Array<Page | Folder>
  defaultOpen: boolean

  constructor(name: string, pages: Array<Page | Folder>, defaultOpen: boolean = false) {
    this.name = name
    this.pages = pages
    this.defaultOpen = defaultOpen
  }
}
