/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
export interface M4Bucket {
  startTime: number
  endTime: number
  gap: boolean
  minValue: number
  maxValue: number
  minValueTime: number
  maxValueTime: number
  firstValue: number
  firstValueTime: number
  lastValue: number
  lastValueTime: number
  sampleCount: number
  valueSum: number
}
export type M4Cache = M4Bucket[]
