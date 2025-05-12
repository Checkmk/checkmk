/**
 * Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { computed, ref, type Ref } from 'vue'

export type LogStepStatus = 'active' | 'completed' | 'pending' | 'error'
export interface LogStep {
  title: string
  status: LogStepStatus
  index: number
}

export interface LogUpdate {
  steps: LogStep[]
}

export type BackgroundJobLogEntries = Readonly<Ref<LogStep[]>>

export interface BackgroundJobLog {
  update: (newLog: LogUpdate | null) => void
  clear: () => void
  isEmpty: () => boolean
  count: () => number
  isTaskActive: () => boolean
  setActiveTasksToError: () => void
  isRunning: Ref<boolean>

  entries: BackgroundJobLogEntries
}

export const useBackgroundJobLog = (displayWaitingAnimation?: boolean): BackgroundJobLog => {
  const entries: Ref<LogStep[]> = ref([])
  const running: Ref<boolean> = ref(false)

  const update = (newLog: LogUpdate | null): void => {
    if (newLog === null || newLog.steps.length === 0) {
      return
    }

    entries.value = []
    entries.value.push(...newLog.steps)
    running.value = true
  }

  const clear = (): void => {
    entries.value = []
    running.value = false
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
    running.value = false
  }

  const isRunning = computed(() => {
    return running.value && !!displayWaitingAnimation
  })

  return {
    update,
    clear,
    isEmpty,
    count,
    isTaskActive,
    setActiveTasksToError,
    entries,
    isRunning
  }
}
