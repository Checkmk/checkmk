/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
// Maps a FastAPI 422 `detail` array to CMK FormSpec's
// `ValidationMessage` shape so per-field errors land on the right inputs.
import type { ValidationMessage } from 'cmk-shared-typing/typescript/vue_formspec_components'

interface PydanticError {
  loc: (string | number)[]
  msg: string
  type?: string
  input?: unknown
  ctx?: Record<string, unknown>
}

// Pydantic's BeforeValidator wraps raised ValueErrors as
// "Value error, <our message>" — strip so the field hint matches the FormSpec
// MatchRegex shown server-side.
function cleanMsg(m: string): string {
  return m.replace(/^Value error,\s*/, '')
}

export interface FormValidationResult {
  messages: ValidationMessage[]
  /** Errors whose top-level field is not in ``knownFields`` (or any error when
   *  ``knownFields`` is omitted, in which case nothing routes to FormEdit). */
  stray: ValidationMessage[]
  summary: string
}

export function toFormValidation(
  detail: unknown,
  knownFields?: Set<string>
): FormValidationResult | null {
  if (!Array.isArray(detail)) {
    return null
  }
  const errs = detail as PydanticError[]
  const first = errs[0]
  if (
    first === undefined ||
    !errs.every((e) => Array.isArray(e?.loc) && typeof e?.msg === 'string')
  ) {
    return null
  }
  const messages: ValidationMessage[] = []
  const stray: ValidationMessage[] = []
  for (const e of errs) {
    const location = e.loc.filter((s) => s !== 'body').map((s) => String(s))
    const item: ValidationMessage = {
      location,
      message: cleanMsg(e.msg),
      replacement_value: e.input ?? null
    }
    const head = location[0]
    if (knownFields && (typeof head !== 'string' || !knownFields.has(head))) {
      stray.push(item)
    } else {
      messages.push(item)
    }
  }
  const field = first.loc.filter((s) => s !== 'body').join('.') || 'value'
  const summary = `${field}: ${cleanMsg(first.msg)}`
  return { messages, stray, summary }
}

/**
 * The field path an error points at, without the wrapper keys and without the
 * trailing name of the union member that failed (``literal[…]``,
 * ``is-instance[…]``) — so two errors about one field collapse onto it.
 */
function fieldNameOf(loc: (string | number)[]): string {
  const identifiers = loc
    .map(String)
    .filter((part) => part !== 'body' && part !== 'config' && /^[A-Za-z_][A-Za-z0-9_]*$/.test(part))
  return identifiers[identifiers.length - 1] ?? ''
}

/** The field errors of a Checkmk REST error body, none for a body shaped otherwise. */
function fieldErrors(body: unknown): PydanticError[] {
  const fields = (body as { fields?: unknown } | null)?.fields
  if (typeof fields !== 'object' || fields === null) {
    return []
  }
  return Object.values(fields as Record<string, unknown>)
    .map((entry) => entry as PydanticError)
    .filter((e) => Array.isArray(e.loc) && typeof e.msg === 'string')
}

/**
 * A Checkmk REST error lists the fields it refused under ``fields``, each with
 * the value that was refused. Naming that value is what makes the difference
 * between "these fields have problems" and something the reader can act on.
 *
 * Returns an empty string for an error shaped some other way, so the caller can
 * fall back to its own message.
 */
export function describeFieldProblems(body: unknown): string {
  const byField = new Map<string, string>()
  for (const { loc, msg, input } of fieldErrors(body)) {
    const field = fieldNameOf(loc)
    if (byField.has(field)) {
      continue
    }
    const got = input === undefined ? '' : ` (got ${JSON.stringify(input)})`
    byField.set(field, field ? `${field}: ${cleanMsg(msg)}${got}` : `${cleanMsg(msg)}${got}`)
  }
  return [...byField.values()].join(' ')
}

/** What the server said about a Livestatus filter, and the filter it said it about. */
export interface FilterRefusal {
  filter: string
  message: string
}

/**
 * What a Checkmk REST error says about the Livestatus filter of the map object
 * at *objectIndex*, which a form shows at that field rather than for the whole
 * object.
 */
export function objectFilterProblem(body: unknown, objectIndex: number): string | null {
  for (const { loc, msg } of fieldErrors(body)) {
    const at = loc.indexOf('objects')
    if (at >= 0 && loc[at + 1] === objectIndex && loc.at(-1) === 'object_filter') {
      return cleanMsg(msg)
    }
  }
  return null
}
