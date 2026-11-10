/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import usei18n from 'cmk-ui-library/lib/i18n'
import type { TranslatedString } from 'cmk-ui-library/lib/i18nString'
import { type ComputedRef, type Ref, computed, ref } from 'vue'

import { useMapsApis } from '@/maps/services/context'
import type { ImageUsage } from '@/maps/types/api'

const UNUSED: ImageUsage = { usage: [], hidden_maps: 0 }

function inUse(found: ImageUsage): boolean {
  return found.usage.length > 0 || found.hidden_maps > 0
}

/**
 * Deleting an image, and what it would break.
 *
 * The maps using the image are looked up before anything is shown, so the
 * operator never sees a plain "delete?" prompt that turns into an in-use
 * warning under their hands. The server checks again on delete: if it finds
 * usage this did not, the warning appears instead of the image being removed.
 */
export function useImageDeletion(
  onDeleted: (name: string) => void,
  onError: (error: unknown, fallback: TranslatedString) => void
): {
  target: Ref<string | null>
  usage: Ref<ImageUsage>
  askedAboutUnused: ComputedRef<boolean>
  askedAboutUsed: ComputedRef<boolean>
  start: (name: string) => Promise<void>
  cancel: () => void
  confirm: () => Promise<void>
} {
  const { images } = useMapsApis()
  const { _t } = usei18n()

  const target = ref<string | null>(null)
  const usage = ref<ImageUsage>(UNUSED)
  /** Nothing is shown until the usage check has answered. */
  const checked = ref(false)

  const askedAboutUnused = computed(
    () => checked.value && target.value !== null && !inUse(usage.value)
  )
  const askedAboutUsed = computed(
    () => checked.value && target.value !== null && inUse(usage.value)
  )

  async function start(name: string): Promise<void> {
    target.value = name
    usage.value = UNUSED
    checked.value = false
    try {
      const found = await images.usage(name)
      // A check for a previously clicked image may resolve late; it must not
      // write its result onto the image now under the cursor.
      if (target.value === name && inUse(found)) {
        usage.value = found
      }
    } catch {
      // Best-effort: a failed check falls through to the plain confirmation.
    } finally {
      if (target.value === name) {
        checked.value = true
      }
    }
  }

  function cancel(): void {
    target.value = null
    usage.value = UNUSED
    checked.value = false
  }

  async function confirm(): Promise<void> {
    const name = target.value
    if (!name) {
      return
    }
    // Forced once usage is known: the operator confirmed it through the in-use
    // warning. Unforced, the server keeps the image and returns the maps.
    const force = inUse(usage.value)
    try {
      const blocking = await images.delete(name, force)
      if (blocking !== null) {
        usage.value = blocking
        return
      }
      onDeleted(name)
      cancel()
    } catch (error: unknown) {
      onError(error, _t('Delete failed'))
      cancel()
    }
  }

  return { target, usage, askedAboutUnused, askedAboutUsed, start, cancel, confirm }
}
