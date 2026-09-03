/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { type Ref, computed, ref, watch } from 'vue'

export interface StagedBackgroundImage {
  /** A picked file, not uploaded until the form is saved. */
  file: Ref<File | null>
  /** Whether saving should drop the map's current background. */
  removed: Ref<boolean>
  /** The picked file as a data: URL, for showing it before it is uploaded. */
  previewUrl: Ref<string | null>
  /** True while either would change what the server has. */
  changed: Ref<boolean>
  pick: (picked: File | null) => void
  setRemoved: (flag: boolean) => void
  reset: () => void
}

/**
 * A background image the operator picked, held until save.
 *
 * Uploading on pick would leave the file on the server even if the operator
 * then closes the form — so the upload happens on save, and until then the
 * preview shows the file as a data: URL. It has to be a data: URL rather than
 * a blob: one: Checkmk's content-security policy allows ``img-src … data:``
 * but blocks blob:, so a blob: URL would render nothing on a real site.
 */
export function useStagedBackgroundImage(): StagedBackgroundImage {
  const file = ref<File | null>(null)
  const removed = ref(false)
  const previewUrl = ref<string | null>(null)

  // Reading a file is asynchronous; a slower read of a file that has since been
  // replaced must not overwrite the newer one.
  let read = 0
  watch(file, (picked) => {
    const mine = ++read
    if (!picked) {
      previewUrl.value = null
      return
    }
    const reader = new FileReader()
    reader.onload = () => {
      if (mine === read) {
        previewUrl.value = reader.result as string
      }
    }
    reader.readAsDataURL(picked)
  })

  const changed = computed(() => file.value !== null || removed.value)

  function reset(): void {
    file.value = null
    removed.value = false
  }

  return {
    file,
    removed,
    previewUrl,
    changed,
    pick: (picked) => {
      file.value = picked
    },
    setRemoved: (flag) => {
      removed.value = flag
    },
    reset
  }
}
