/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { JUnitTestCase } from './types'

function decodeXml(s: string): string {
  return s
    .replace(/&lt;/g, '<')
    .replace(/&gt;/g, '>')
    .replace(/&quot;/g, '"')
    .replace(/&apos;/g, "'")
    .replace(/&amp;/g, '&')
}

export function parseJunitXml(xml: string): JUnitTestCase[] {
  const cases: JUnitTestCase[] = []
  const tcRegex = /<testcase\b([^>]*?)(?:\/>|>([\s\S]*?)<\/testcase>)/g
  const attr = (s: string, k: string): string | undefined => {
    const r = new RegExp(`\\b${k}="([^"]*)"`).exec(s)
    return r ? decodeXml(r[1]) : undefined
  }
  let m: RegExpExecArray | null
  while ((m = tcRegex.exec(xml)) !== null) {
    const attrs = m[1]
    const body = m[2] || ''
    const classname = attr(attrs, 'classname') || ''
    const name = attr(attrs, 'name') || ''
    if (!name) continue
    const time = parseFloat(attr(attrs, 'time') || '0')
    const file = attr(attrs, 'file')
    const lineStr = attr(attrs, 'line')
    const line = lineStr ? parseInt(lineStr, 10) : undefined
    let status: JUnitTestCase['status'] = 'passed'
    let message: string | undefined
    let details: string | undefined
    const failure = /<(failure|error)\b([^>]*?)(?:\/>|>([\s\S]*?)<\/\1>)/.exec(body)
    const skipped = /<skipped\b([^>]*?)(?:\/>|>([\s\S]*?)<\/skipped>)/.exec(body)
    if (failure) {
      status = failure[1] === 'failure' ? 'failed' : 'error'
      message = attr(failure[2], 'message')
      details = decodeXml((failure[3] || '').trim()) || undefined
    } else if (skipped) {
      status = 'skipped'
      message = attr(skipped[1], 'message')
    }
    cases.push({ classname, name, file, line, time, status, message, details })
  }
  return cases
}

export function extractSystemOut(xml: string): string {
  const m = /<system-out>([\s\S]*?)<\/system-out>/.exec(xml)
  if (!m) return ''
  let text = m[1]
  const cm = /<!\[CDATA\[([\s\S]*?)\]\]>/.exec(text)
  if (cm) text = cm[1]
  return text
}

// eslint-disable-next-line no-control-regex
const ANSI_RE = /\x1B\[[0-9;]*[a-zA-Z]/g

export function stripAnsi(s: string): string {
  return s.replace(ANSI_RE, '')
}
