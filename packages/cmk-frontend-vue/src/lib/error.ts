/**
 * Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */

export function formatError(error: Error | CmkError): string {
  const errors: Array<Error | CmkError> = []
  let c: Error = error
  while (c) {
    errors.push(c)
    c = (typeof c === 'object' && c !== null && 'cause' in c && c.cause) as Error
  }

  return errors
    .map((error: Error | CmkError) => {
      let stack: Array<string> = []
      if (error.stack) {
        stack = error.stack.split('\n')
        if (stack.length > 12) {
          stack = stack.slice(0, 8)
          stack.push('...')
        }
      }
      let context = ''
      if (error instanceof CmkError) {
        context = error.getContext()
        if (context) {
          context = `\n\n${context}`
        }
      }
      return `${error.name}: ${error.message}${context}\n\n${stack.join('\n')}`
    })
    .join('\n\n')
}

export class CmkError<T extends Error = Error> extends Error {
  cause: T | null

  constructor(message: string, cause: T | null) {
    super(message)
    this.name = 'CmkError'
    this.cause = cause
  }

  getContext(): string {
    // you can add additional details in your specific implementation
    return ''
  }
}

export class CmkSimpleError extends CmkError {
  constructor(message: string) {
    super(message, null)
    this.name = 'CmkSimpleError'
  }
}
