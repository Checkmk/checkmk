/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import usei18n from 'cmk-ui-library/lib/i18n'
import type { TranslatedString } from 'cmk-ui-library/lib/i18nString'
import { type Ref, onBeforeUnmount, onMounted, ref, watch } from 'vue'

import { downloadBlob } from '@/lib/downloadBlob'

import {
  type MonitoringService,
  RowsNotLoadedError
} from '@/monitoring/shared/services/MonitoringService'

import { type ExportFormat, REPORT_FORMAT, RowExport } from './rowExport'

export interface RowExportFeedback {
  variant: 'loading' | 'warning' | 'error'
  text: TranslatedString
}

export type ExportCounts = { exported: string; matched: string }

export interface RowExportTexts {
  exporting: TranslatedString
  notLoaded: TranslatedString
  truncated: (counts: ExportCounts, canShowMore: boolean) => TranslatedString
}

export interface RowExportOptions {
  exportEvent: string
  build: () => Promise<{ file(format: ExportFormat): File }>
  texts: RowExportTexts
  openReport?: () => void
}

export function useRowExport<T>(
  service: MonitoringService<T>,
  options: RowExportOptions
): Ref<RowExportFeedback | null> {
  const { _t } = usei18n()
  const feedback = ref<RowExportFeedback | null>(null)
  const count = new Intl.NumberFormat()

  async function exportRows(format: ExportFormat): Promise<void> {
    feedback.value = { variant: 'loading', text: options.texts.exporting }
    try {
      const file = (await options.build()).file(format)
      downloadBlob(file.name, file)
    } catch (error: unknown) {
      feedback.value = {
        variant: 'error',
        text:
          error instanceof RowsNotLoadedError
            ? options.texts.notLoaded
            : _t('The export failed: %{error}', { error: String(error) })
      }
      return
    }
    const exported = service.items.value.length
    const matched = service.matched.value
    const limits = service.offeredLimits
    feedback.value =
      exported < matched
        ? {
            variant: 'warning',
            text: options.texts.truncated(
              { exported: count.format(exported), matched: count.format(matched) },
              limits.indexOf(service.requestedLimit.value) < limits.length - 1
            )
          }
        : null
  }

  function openReport(): void {
    if (options.openReport === undefined) {
      feedback.value = { variant: 'error', text: _t('This page offers no PDF report.') }
      return
    }
    feedback.value = null
    options.openReport()
  }

  function onExport(event: Event): void {
    const format: unknown = event instanceof CustomEvent ? event.detail : undefined
    if (format === REPORT_FORMAT) {
      openReport()
    } else if (RowExport.isFormat(format)) {
      void exportRows(format)
    }
  }

  watch(service.fetchState, (state) => {
    if (state === 'foreground' && feedback.value?.variant !== 'loading') {
      feedback.value = null
    }
  })

  onMounted(() => {
    document.addEventListener(options.exportEvent, onExport)
  })

  onBeforeUnmount(() => {
    document.removeEventListener(options.exportEvent, onExport)
  })

  return feedback
}
