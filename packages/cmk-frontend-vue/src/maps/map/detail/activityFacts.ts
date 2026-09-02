/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
/**
 * What the activity tab states: what people have written on this object and
 * what downtimes are on it.
 *
 * Both are relative to "now", so the caller passes the tick that drives the
 * drawer's ageing labels rather than each row reading the clock itself.
 */
import type { ObjectDetails } from '@/maps/types/api'
import type { TranslateFn } from '@/maps/utils/dropdownOptions'
import { formatRelativeDuration, formatRelativeFuture } from '@/maps/utils/time'

export interface CommentRow {
  id: number
  author: string
  text: string
  age: string
  /** When the comment goes away on its own, if it does. */
  expires: string | null
}

export function commentRows(
  details: ObjectDetails | null,
  nowMs: number,
  _t: TranslateFn
): CommentRow[] {
  return (details?.comments ?? []).map((comment) => ({
    id: comment.id,
    author: comment.author || '?',
    text: comment.comment,
    age: _t('%{duration} ago', {
      duration: formatRelativeDuration(comment.entry_time, nowMs)
    }),
    expires:
      comment.expire_time && comment.expire_time > 0
        ? _t('in %{duration}', {
            duration: formatRelativeFuture(comment.expire_time, nowMs)
          })
        : null
  }))
}

export interface DowntimeRow {
  id: number
  author: string
  comment: string
  timeRange: string
  /** A fixed downtime runs on the clock; a flexible one waits for a problem. */
  fixed: boolean
}

function formatDateTime(seconds: number): string {
  return new Date(seconds * 1000).toLocaleString(undefined, {
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit'
  })
}

export function downtimeRows(details: ObjectDetails | null): DowntimeRow[] {
  return (details?.downtimes ?? []).map((downtime) => ({
    id: downtime.id,
    author: downtime.author || '?',
    comment: downtime.comment,
    timeRange: `${formatDateTime(downtime.start_time)} → ${formatDateTime(downtime.end_time)}`,
    fixed: downtime.fixed
  }))
}

/** How many entries the tab holds -- shown on the tab itself. */
export function activityCount(details: ObjectDetails | null): number {
  return (details?.comments?.length ?? 0) + (details?.downtimes?.length ?? 0)
}
