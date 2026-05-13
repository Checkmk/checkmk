/**
 * Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { TranslatedString } from '@/lib/i18nString'

import type { Section } from './types'

export interface Suggestion {
  name: string | null /* name is null for unselectable suggestions */
  title: TranslatedString
}

export class ErrorResponse {
  error: string

  constructor(error: string) {
    this.error = error
  }
}

export class WarningResponse {
  warning: string
  choices: Array<Suggestion> | Array<Section>

  constructor(warning: string, choices: Array<Suggestion> | Array<Section> = []) {
    this.warning = warning
    this.choices = choices
  }
}

export class Response {
  choices: Array<Suggestion> | Array<Section>

  constructor(choices: Array<Suggestion> | Array<Section>) {
    this.choices = choices
  }
}
