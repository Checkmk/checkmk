/**
 * Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { readonly, ref, type Ref } from 'vue'

export type WizardMode = 'guided' | 'overview'
export interface WizardHook {
  stages: Ref<number>
  stage: Ref<number>
  mode: Ref<WizardMode>
  next: () => void
  prev: () => void
  goto: (index: number) => void
  rewind: () => void
  setMode: (mode: WizardMode) => void
  toggleMode: () => void
}

/**
 * Hook to manage a wizard like flow. Note that the name has been chosen on purpose
 * @param {number} stagesCount - The number of stages in the wizard. Including the save stage
 * @param {boolean} guidedMode - If true, the wizard will display guided mode, otherwise will display overview mode
 * @returns {WizardHook} - The wizard hook, emm... the composable
 */

const useWizard = (stagesCount: number, mode: WizardMode = 'guided'): WizardHook => {
  /**
   * The number of stages in the wizard
   */
  const stages = ref(stagesCount)

  /**
   * The current stage
   */
  const stage = ref(0)

  /**
   * The wizard layout mode
   */
  const wizardMode: Ref<WizardMode> = ref(mode)

  /**
   * Move to the first stage
   * @returns {number | null} - The stage we moved to
   */
  const rewind = (): number | null => {
    return goto(0)
  }

  /**
   * Jump to the previous stage
   * @returns {number | null} - The stage we moved to
   */
  const prev = (): number | null => {
    return goto(stage.value - 1)
  }

  /**
   * Jump to the next stage
   * @returns {number | null} - The stage we moved to
   */
  const next = (): number | null => {
    return goto(stage.value + 1)
  }

  /**
   * Go to a specific stage. wizard must be running in stages layout
   * and the index must be within 0..stages-1
   * @param {number} index - Jump to a specific stage
   * @returns {number | null} - The stage we moved to
   */
  const goto = (index: number): number | null => {
    if (wizardMode.value === 'overview' || index < 0 || index >= stages.value) {
      return null
    }

    stage.value = index

    return stage.value
  }

  /**
   * Switch the layout between guided mode and overview mode
   * @param { WizardMode } mode - The mode to switch to
   */
  const setMode = (mode: WizardMode) => {
    wizardMode.value = mode
  }

  /**
   * Toggle between guided mode and overview mode
   */
  const toggleMode = () => {
    wizardMode.value = wizardMode.value === 'guided' ? 'overview' : 'guided'
  }

  return {
    stages: readonly(stages),
    stage: readonly(stage),
    mode: readonly(wizardMode),
    setMode,
    toggleMode,
    rewind,
    prev,
    next,
    goto
  }
}

export default useWizard
