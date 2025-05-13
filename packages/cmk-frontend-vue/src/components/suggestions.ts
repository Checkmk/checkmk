/**
 * Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */

export interface Suggestion {
  name: string | null /* name is null for unselectable suggestions */
  title: string
}

export class ErrorResponse {
  error: string

  constructor(error: string) {
    this.error = error
  }
}

export class Response {
  choices: Array<Suggestion>

  constructor(choices: Array<Suggestion>) {
    this.choices = choices
  }
}
