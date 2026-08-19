/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import usei18n from 'cmk-ui-library/lib/i18n'
import type { TranslatedString } from 'cmk-ui-library/lib/i18nString'
import { useDebounceFn } from 'cmk-ui-library/lib/useDebounce'
import { type MaybeRefOrGetter, type Ref, computed, ref, toValue, watch } from 'vue'

import type { Domain, GraphItem, ItemId } from '../../types'
import {
  type ArithmeticNode,
  type FunctionName,
  type OperatorSymbol,
  type ParseErrorDetail,
  isOperatorSymbol,
  parseFormula,
  validateFormula
} from '../formula'
import type { CommitResult } from '../types'
import { useFormulaMessages } from './useFormulaMessages'

const VALIDATION_DELAY_MS = 1500

export interface FormulaEditor {
  text: Ref<string>
  errors: Ref<string[]>
  appendOperator: (symbol: OperatorSymbol) => void
  wrapFunction: (name: FunctionName) => void
  appendRef: (id: ItemId) => void
  commit: () => CommitResult
  reset: () => void
}

export function useFormulaEditor(
  items: MaybeRefOrGetter<readonly GraphItem[]>,
  domain: Domain,
  editedItemId: MaybeRefOrGetter<ItemId | null> = null
): FormulaEditor {
  const { _t } = usei18n()
  const { issueMessage } = useFormulaMessages()
  const text = ref('')
  const errors = ref<string[]>([])

  function parseMessage(detail: ParseErrorDetail): TranslatedString {
    switch (detail.code) {
      case 'empty-formula':
        return _t('The formula is empty; add a metric id (e.g. A) or a number.')
      case 'invalid-number':
        return _t("Invalid number; use digits with an optional decimal point (e.g. '1.5').")
      case 'unexpected-character':
        return _t(
          "Unexpected character '%{character}'; allowed are ids (A, B, ...), numbers, " +
            'operators (+ - * /), parentheses and commas.',
          { character: detail.character }
        )
      case 'unexpected-token':
        return _t("Unexpected '%{token}'; join values with an operator (+ - * /).", {
          token: detail.token
        })
      case 'unexpected-end':
        return _t('The formula ends unexpectedly; add a metric id (e.g. A) or a number.')
      case 'unknown-function':
        return _t("Unknown function '%{name}'; available functions: %{available}.", {
          name: detail.name,
          available: detail.available.join(', ')
        })
      case 'empty-function-args':
        return _t("'%{name}()' needs at least one argument, e.g. '%{name}(A)'.", {
          name: detail.name
        })
      case 'expected-token':
        return _t("Expected '%{symbol}'.", { symbol: detail.symbol })
      case 'nesting-too-deep':
        return _t('The formula is nested too deeply; simplify it.')
    }
  }

  type Evaluation =
    | { status: 'empty'; errors: [] }
    | { status: 'parse-error'; errors: string[] }
    | { status: 'invalid'; errors: string[] }
    | { status: 'valid'; ast: ArithmeticNode; errors: [] }

  const evaluation = computed<Evaluation>(() => {
    if (text.value.trim() === '') {
      return { status: 'empty', errors: [] }
    }
    const result = parseFormula(text.value)
    if ('error' in result) {
      return {
        status: 'parse-error',
        errors: [_t('Invalid formula: %{detail}', { detail: parseMessage(result.error.detail) })]
      }
    }
    const issues = validateFormula(result.ast, toValue(items), domain, toValue(editedItemId))
    if (issues.length > 0) {
      return { status: 'invalid', errors: issues.map(issueMessage) }
    }
    return { status: 'valid', ast: result.ast, errors: [] }
  })

  const showValidation = useDebounceFn(() => {
    const messages = evaluation.value.errors
    if (messages.length > 0) {
      errors.value = messages
    }
  }, VALIDATION_DELAY_MS)

  watch(
    () => evaluation.value.errors,
    (messages) => {
      if (messages.length === 0) {
        errors.value = []
        return
      }
      showValidation()
    }
  )

  function appendOperator(symbol: OperatorSymbol): void {
    const trimmed = text.value.replace(/\s+$/, '')
    text.value = trimmed === '' ? `${symbol} ` : `${trimmed} ${symbol} `
  }

  function wrapFunction(name: FunctionName): void {
    text.value = `${name}(${text.value.trim()})`
  }

  function appendRef(id: ItemId): void {
    const trimmed = text.value.replace(/\s+$/, '')
    if (trimmed === '') {
      text.value = id
      return
    }
    const last = trimmed[trimmed.length - 1]!
    if (/[A-Za-z0-9)]/.test(last)) {
      text.value = `${trimmed} ${lastOperator(trimmed) ?? '+'} ${id}`
    } else if (last === '(') {
      text.value = `${trimmed}${id}`
    } else {
      text.value = `${trimmed} ${id}`
    }
  }

  function commit(): CommitResult {
    const result = evaluation.value
    if (result.status === 'empty') {
      const messages = [parseMessage({ code: 'empty-formula' })]
      errors.value = messages
      return { errors: messages }
    }
    errors.value = result.errors
    return result.status === 'valid' ? { ast: result.ast } : { errors: result.errors }
  }

  function reset(): void {
    text.value = ''
    errors.value = []
  }

  return { text, errors, appendOperator, wrapFunction, appendRef, commit, reset }
}

/** The most recent binary operator symbol in the text, or null if there is none. */
function lastOperator(text: string): OperatorSymbol | null {
  for (let i = text.length - 1; i >= 0; i--) {
    const ch = text[i]!
    if (isOperatorSymbol(ch)) {
      return ch
    }
  }
  return null
}
