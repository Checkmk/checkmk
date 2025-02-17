/**
 * Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { ref, type Ref } from 'vue'

export type LogStepStatus = 'active' | 'completed' | 'pending' | 'error'
export interface LogStep {
  title: string
  status: LogStepStatus
  index: number
}

export interface LogUpdate {
  steps: LogStep[]
}

interface BackgroundJobLog {
  update: (newLog: LogUpdate | null) => void
  clear: () => void
  isEmpty: () => boolean
  count: () => number
  isTaskActive: () => boolean
  setActiveTasksToError: () => void

  entries: Readonly<Ref<LogStep[]>>
}

export const useBackgroundJobLog = (): BackgroundJobLog => {
  const entries: Ref<LogStep[]> = ref([])

  const update = (newLog: LogUpdate | null): void => {
    clear()
    if (newLog === null || newLog.steps.length === 0) {
      return
    }

    entries.value = []
    entries.value.push(...newLog.steps)
  }

  const clear = (): void => {
    entries.value = []
  }

  const isEmpty = (): boolean => {
    return entries.value.length === 0
  }

  const count = (): number => {
    return entries.value.length
  }

  const isTaskActive = (): boolean => {
    return entries.value.some((step) => step.status === 'active')
  }

  const setActiveTasksToError = (): void => {
    entries.value.forEach((step) => {
      if (step.status === 'active') {
        step.status = 'error'
      }
    })
  }

  return {
    update,
    clear,
    isEmpty,
    count,
    isTaskActive,
    setActiveTasksToError,
    entries: entries
  }
}
