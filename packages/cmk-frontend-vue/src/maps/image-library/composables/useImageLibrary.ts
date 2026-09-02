/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import usei18n from 'cmk-ui-library/lib/i18n'
import type { TranslatedString } from 'cmk-ui-library/lib/i18nString'
import { type ComputedRef, type Ref, computed, onMounted, ref } from 'vue'

import { useMapsApis } from '@/maps/services/context'
import { errorText } from '@/maps/shared/errorText'
import type { ImageEntry } from '@/maps/types/api'

/**
 * The images a site has for its maps: the ones an operator uploaded and the
 * built-in library, searchable by name.
 *
 * Uploads are per file rather than one batch call, so one rejected file does
 * not lose the others — the list is re-read afterwards and the first failure is
 * reported.
 */
export function useImageLibrary(): {
  loading: Ref<boolean>
  query: Ref<string>
  errorMessage: Ref<TranslatedString | null>
  hasUploads: ComputedRef<boolean>
  matchingUploaded: ComputedRef<ImageEntry[]>
  matchingBuiltin: ComputedRef<ImageEntry[]>
  uploadFiles: (event: Event) => Promise<void>
  forget: (name: string) => void
  reportError: (error: unknown, fallback: TranslatedString) => void
} {
  const { images } = useMapsApis()
  const { _t } = usei18n()

  const all = ref<ImageEntry[]>([])
  const loading = ref(false)
  const query = ref('')
  /** Whatever went wrong last, be it an upload or a delete. */
  const errorMessage = ref<TranslatedString | null>(null)

  const uploaded = computed(() => all.value.filter((image) => !image.builtin))
  const builtin = computed(() => all.value.filter((image) => image.builtin))
  const hasUploads = computed(() => uploaded.value.length > 0)

  /** The search needle is derived once per search, not once per image. */
  function matching(candidates: ComputedRef<ImageEntry[]>): ComputedRef<ImageEntry[]> {
    return computed(() => {
      const needle = query.value.trim().toLowerCase()
      if (needle === '') {
        return candidates.value
      }
      return candidates.value.filter((image) => image.name.toLowerCase().includes(needle))
    })
  }

  const matchingUploaded = matching(uploaded)
  const matchingBuiltin = matching(builtin)

  function reportError(error: unknown, fallback: TranslatedString): void {
    errorMessage.value = errorText(error, fallback)
  }

  async function fetchImages(): Promise<void> {
    loading.value = true
    try {
      all.value = await images.list()
    } finally {
      loading.value = false
    }
  }

  async function uploadFiles(event: Event): Promise<void> {
    const input = event.target as HTMLInputElement
    const files = input.files
    if (!files?.length) {
      return
    }
    errorMessage.value = null
    try {
      const results = await Promise.allSettled(Array.from(files).map((file) => images.upload(file)))
      await fetchImages()
      const failed = results.find(
        (result): result is PromiseRejectedResult => result.status === 'rejected'
      )
      if (failed) {
        reportError(failed.reason, _t('Upload failed'))
      }
    } catch (error: unknown) {
      reportError(error, _t('Upload failed'))
    } finally {
      // Cleared so picking the same file again still fires a change event.
      input.value = ''
    }
  }

  /** Drops a deleted image from the list without re-reading the whole library. */
  function forget(name: string): void {
    all.value = all.value.filter((image) => image.name !== name)
  }

  onMounted(fetchImages)

  return {
    loading,
    query,
    errorMessage,
    hasUploads,
    matchingUploaded,
    matchingBuiltin,
    uploadFiles,
    forget,
    reportError
  }
}
