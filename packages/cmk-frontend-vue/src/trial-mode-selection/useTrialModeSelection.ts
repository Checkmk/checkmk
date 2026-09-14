/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { type TrialModeSelectionProps } from 'cmk-shared-typing/typescript/trial_mode_selection_props'
import {
  type TrialModeSelectionRequest,
  type VerificationMode
} from 'cmk-shared-typing/typescript/trial_mode_selection_request'
import { cmkAjax } from 'cmk-ui-library/lib/ajax'
import { ref } from 'vue'

import { getCsrfToken } from '@/lib/csrf'

/**
 * Screens the gate dialog can show. The customer branch is a single step, asking how the
 * license is verified; the trial branch walks choice -> email -> code -> success, and
 * the last two steps arrive with the rest of CMK-37568.
 */
export type TrialModeScreen = 'choice' | 'verification' | 'email' | 'code' | 'success'

/**
 * State shared by the dialog's screens.
 *
 * A factory rather than module-scoped state: the screens are mounted once per page, and
 * a shared singleton would carry state between tests.
 */
export function useTrialModeSelection(props: TrialModeSelectionProps) {
  const screen = ref<TrialModeScreen>('choice')
  const saving = ref(false)
  const saveFailed = ref(false)

  function goTo(next: TrialModeScreen): void {
    // A save in flight navigates away on its own once it succeeds, so leaving the
    // screen it was started from would race it.
    if (saving.value) {
      return
    }
    saveFailed.value = false
    screen.value = next
  }

  /**
   * Records the decision for the whole site and only then leaves the gate.
   *
   * Until this runs the gate stays closed and re-prompts on the next admin login,
   * which is what makes an abandoned dialog reappear.
   */
  async function persistAndLeave(
    request: TrialModeSelectionRequest,
    target: string
  ): Promise<void> {
    if (saving.value) {
      return
    }
    saving.value = true
    saveFailed.value = false
    try {
      await cmkAjax(props.save_url, {
        ...request,
        _csrf_token: getCsrfToken()
      })
      window.location.assign(target)
    } catch (e) {
      saving.value = false
      saveFailed.value = true
      console.error(e)
    }
  }

  function verifyNow(mode: VerificationMode): Promise<void> {
    return persistAndLeave(
      { selection: 'customer', verification_mode: mode },
      mode === 'online' ? props.verify_online_url : props.verify_offline_url
    )
  }

  function verifyLater(): Promise<void> {
    return persistAndLeave({ selection: 'customer' }, 'index.py')
  }

  return {
    screen,
    saving,
    saveFailed,
    goTo,
    verifyNow,
    verifyLater
  }
}
