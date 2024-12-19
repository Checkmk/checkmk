/**
 * Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { Component } from 'vue'

export class Page {
  name: string
  component: Component<{ screenshotMode: boolean }>

  constructor(name: string, component: Component<{ screenshotMode: boolean }>) {
    this.name = name
    this.component = component
  }
}

export class Folder {
  name: string
  component: Component<{ screenshotMode: boolean }>
  pages: Array<Page | Folder>

  constructor(
    name: string,
    component: Component<{ screenshotMode: boolean }>,
    pages: Array<Page | Folder>
  ) {
    this.name = name
    this.component = component
    this.pages = pages
  }
}

export class RootFolder {
  component: Component<{ screenshotMode: boolean }>
  pages: Array<Page | Folder>

  constructor(component: Component<{ screenshotMode: boolean }>, pages: Array<Page | Folder>) {
    this.component = component
    this.pages = pages
  }
}
