/**
 * Copyright (C) 2024 Checkmk GmbH - License: Checkmk Enterprise License
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */

interface Element {
  ident: string
  title: string
}

export interface Topic {
  ident: string
  title: string
  elements: Element[]
}

export interface SpecLineType {
  line: string
  area: string
  stack: string
}
