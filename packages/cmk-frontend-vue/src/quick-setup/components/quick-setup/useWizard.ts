/**
 * Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { readonly, ref, type Ref } from 'vue'

export type WizardMode = 'guided' | 'overview'
export interface WizardHook {
  // Current stage and stage count
  stages: Ref<number>
  stage: Ref<number>

  // Wizard mode
  mode: Ref<WizardMode>
  setMode: (mode: WizardMode) => void
  toggleMode: () => void

  // Movement functions
  next: () => number
  prev: () => number
  goto: (index: number) => number
  rewind: () => number

  // Enable / Disable stages
  enableStage: (index: number) => void
  disableStage: (index: number) => void
  setStageStatus: (index: number, enabled: boolean) => void
  isStageEnabled: (index: number) => boolean
}

/**
 * Hook to manage a wizard like flow. Note that the name has been chosen on purpose
 * @param {number} stagesCount - The number of stages in the wizard. Including the save stage
 * @param {WizardMode} mode - The mode the wizar will start in. By default it is guided
 * @returns {WizardHook} - The wizard hook, emm... the composable
 */

const useWizard = (stagesCount: number, mode: WizardMode = 'guided'): WizardHook => {
  /**
   * The number of stages in the wizard
   */
  const stages = ref(stagesCount)

  /**
   * Set of disabled stage indexes
   */
  const disabledStages = new Set<number>()

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
   * @returns {number} - The stage we moved to
   */
  const rewind = (): number => {
    return goto(0)
  }

  /**
   * Jump to the previous stage
   * @returns {number} - The stage we moved to
   */
  const prev = (): number => {
    return goto(_findNextEnabledStage(-1))
  }

  /**
   * Jump to the next stage
   * @returns {number} - The stage we moved to
   */
  const next = (): number => {
    return goto(_findNextEnabledStage())
  }

  /**
   * Go to a specific stage. wizard must be running in stages layout
   * and the index must be within 0..stages-1
   * @param {number} index - Jump to a specific stage
   * @returns {number} - The stage we moved to. Could be the same as the current stage
   */
  const goto = (index: number): number => {
    if (
      wizardMode.value === 'overview' ||
      index < 0 ||
      index === stage.value ||
      index >= stages.value ||
      disabledStages.has(index)
    ) {
      return stage.value
    }

    stage.value = index

    return stage.value
  }

  /**
   * Switch the layout between guided mode and overview mode. If going to overview mode, then we move to the first stage
   * @param { WizardMode } mode - The mode to switch to
   */
  const setMode = (mode: WizardMode) => {
    if (wizardMode.value === mode) {
      return
    }

    wizardMode.value = mode

    if (mode === 'overview') {
      stage.value = 0
    }
  }

  /**
   * Toggle between guided mode and overview mode
   */
  const toggleMode = () => {
    setMode(wizardMode.value === 'guided' ? 'overview' : 'guided')
  }

  /**
   * Finds the next enabled stage in ascending or descending direction
   * @param {1 | -1 } direction - if 1, we search in ascending order, if -1, we search in descending order
   * @returns number - The next enabled stage
   */
  const _findNextEnabledStage = (direction: 1 | -1 = 1): number => {
    let nextStage = stage.value + direction

    while (nextStage >= 0 && nextStage < stages.value) {
      if (!disabledStages.has(nextStage)) {
        return nextStage
      }

      nextStage += direction
    }

    //If no stage is found, we return the current stage
    return stage.value
  }

  const enableStage = (index: number) => disabledStages.delete(index)

  const disableStage = (index: number) => {
    if (index > 0 && index < stages.value && stage.value !== index) {
      disabledStages.add(index)
    }
  }

  const setStageStatus = (index: number, enabled: boolean) => {
    if (enabled) {
      enableStage(index)
    } else {
      disableStage(index)
    }
  }

  const isStageEnabled = (index: number) => !disabledStages.has(index)

  return {
    // Stage count and current stage
    stages: readonly(stages),
    stage: readonly(stage),

    // Wizard mode (guided or overview )
    mode: readonly(wizardMode),
    setMode,
    toggleMode,

    //Movement functions
    rewind,
    prev,
    next,
    goto,

    //Stage enable / disable
    enableStage,
    disableStage,
    setStageStatus,
    isStageEnabled
  }
}

export default useWizard
