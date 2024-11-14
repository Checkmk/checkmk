<!--
Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { computed, ref, toValue, type Ref, watch, provide, readonly } from 'vue'
import QuickSetup from './components/quick-setup/QuickSetup.vue'

import {
  saveQuickSetup,
  getOverview,
  validateStage,
  getAllStages,
  editQuickSetup
} from './rest_api'
import { formDataKey } from './keys'
import useWizard, { type WizardMode } from './components/quick-setup/useWizard'
import type { ComponentSpec } from './components/quick-setup/widgets/widget_types'
import { renderContent, renderRecap, defineButtons } from './render_utils'
import type {
  QuickSetupSaveStageSpec,
  QuickSetupStageSpec,
  StageButtonSpec
} from './components/quick-setup/quick_setup_types'
import { type QuickSetupAppProps } from './types'
import type {
  QSInitializationResponse,
  ValidationError,
  GeneralError,
  RestApiError,
  QSStageResponse
} from './rest_api_types'
import { asStringArray } from './utils'
import type {
  StageData,
  AllValidationMessages
} from '@/quick-setup/components/quick-setup/widgets/widget_types'
import ToggleButtonGroup from '@/components/ToggleButtonGroup.vue'
import usePersistentRef from '@/lib/usePersistentRef'
/**
 * Type definition for internal stage storage
 */
interface QSStageStore {
  title: string
  sub_title?: string | null
  components?: ComponentSpec[]
  recap?: ComponentSpec[]
  user_input: Ref<StageData>
  form_spec_errors?: AllValidationMessages
  errors?: string[]
  buttons?: StageButtonSpec[]
  load_wait_label: string
}

const GUIDED_MODE = 'guided'
const OVERVIEW_MODE = 'overview'

let guidedModeLabel = ''
let overviewModeLabel = ''

const props = withDefaults(defineProps<QuickSetupAppProps>(), {
  mode: 'guided',
  toggleEnabled: false
})

const loadedAllStages = ref(false)
const showQuickSetup = ref(false)
const stages = ref<QSStageStore[]>([])
const globalError = ref<string | null>(null) //Main error message
const loading: Ref<boolean> = ref(false) // Loading flag

const numberOfStages = computed(() => stages.value.length) //Number of stages

// Data from all stages
const formData = ref<{ [key: number]: StageData }>({})
provide(formDataKey, readonly(formData))

//
//
// Stages flow control and user input update
//
//
const nextStage = async () => {
  loading.value = true
  globalError.value = null

  const thisStage = quickSetupHook.stage.value
  const nextStage = quickSetupHook.stage.value + 1

  const userInput: StageData[] = []

  for (let i = 0; i <= thisStage; i++) {
    const formData = (toValue(stages.value[i]!.user_input) || {}) as StageData
    userInput.push(formData)
  }

  let result: QSStageResponse | null = null

  try {
    result = await validateStage(props.quick_setup_id, userInput, props.objectId)
  } catch (err) {
    handleError(err as RestApiError)
  }

  loading.value = false
  if (!result) {
    return
  }

  //Clear form_spec_errors and other_errors from thisStage
  stages.value[thisStage]!.form_spec_errors = {}
  stages.value[thisStage]!.errors = []

  stages.value[thisStage]!.recap = result.stage_recap

  //If we have not finished the quick setup yet, but still on the, regular step
  if (nextStage < numberOfStages.value - 1) {
    const btn = []
    if (result.next_stage_structure.next_button) {
      btn.push(
        defineButton.next(
          result.next_stage_structure.next_button.label,
          result.next_stage_structure.next_button.aria_label
        )
      )
    }

    if (result.next_stage_structure.prev_button) {
      btn.push(
        defineButton.prev(
          result.next_stage_structure.prev_button.label,
          result.next_stage_structure.prev_button.aria_label
        )
      )
    }

    stages.value[nextStage] = {
      ...stages.value[nextStage]!,
      components: result.next_stage_structure.components,
      recap: [],
      form_spec_errors: {},
      errors: [],
      buttons: btn,
      load_wait_label: result.next_stage_structure.load_wait_label
    }
  }

  quickSetupHook.next()
}

const prevStage = () => {
  globalError.value = null
  quickSetupHook.prev()
}

const loadAllStages = async (): Promise<QSStageStore[]> => {
  const data = await getAllStages(props.quick_setup_id, props.objectId)
  const result: QSStageStore[] = []

  guidedModeLabel = data.guided_mode_string
  overviewModeLabel = data.overview_mode_string

  for (let stageIndex = 0; stageIndex < data.stages.length; stageIndex++) {
    const stage = data.stages[stageIndex]!
    const btn: StageButtonSpec[] = []
    if (stageIndex !== data.stages.length - 1) {
      btn.push(defineButton.next(stage.next_button!.label, stage.next_button!.aria_label))
    }

    if (stageIndex !== 0) {
      btn.push(defineButton.prev(stage.prev_button!.label, stage.prev_button!.aria_label))
    }

    const userInput = stages.value[stageIndex]?.user_input || {}
    result.push({
      title: stage.title,
      sub_title: stage?.sub_title || null,
      components: stage.components || [],
      recap: [],
      form_spec_errors: {},
      errors: [],
      user_input: ref(userInput),
      buttons: btn,
      load_wait_label: stage.load_wait_label
    })
  }

  // Add save stage
  result.push({
    title: '',
    sub_title: null,
    components: [],
    recap: [],
    form_spec_errors: {},
    errors: [],
    user_input: ref({}),
    buttons: [
      ...data.complete_buttons.map((button) =>
        defineButton.save(button.id, button.label, button.ariaLabel)
      ),
      defineButton.prev(data.prev_button.label, data.prev_button.aria_label)
    ],
    load_wait_label: ''
  })
  loadedAllStages.value = true
  return result
}

const loadGuidedStages = async (): Promise<QSStageStore[]> => {
  const data: QSInitializationResponse = await getOverview(props.quick_setup_id, props.objectId)
  const result: QSStageStore[] = []

  guidedModeLabel = data.guided_mode_string
  overviewModeLabel = data.overview_mode_string

  //Load stages
  for (let index = 0; index < data.overviews.length; index++) {
    const isFirst = index === 0
    const overview = data.overviews[index]!

    const userInput = stages.value[index]?.user_input || {}

    const btn = []
    if (isFirst) {
      btn.push(
        defineButton.next(
          data.stage.next_stage_structure.next_button!.label,
          data.stage.next_stage_structure.next_button!.aria_label
        )
      )
    }

    result.push({
      title: overview.title,
      sub_title: overview.sub_title || null,
      components: isFirst ? data.stage.next_stage_structure.components : [],
      recap: [],
      form_spec_errors: {},
      errors: [],
      user_input: ref(userInput),
      buttons: btn,
      load_wait_label: isFirst ? data.stage.next_stage_structure.load_wait_label : ''
    })
  }

  // Add save stage
  result.push({
    title: '',
    sub_title: null,
    components: [],
    recap: [],
    form_spec_errors: {},
    errors: [],
    user_input: ref({}),
    buttons: [
      ...data.complete_buttons.map((button) =>
        defineButton.save(button.id, button.label, button.ariaLabel)
      ),
      defineButton.prev(data.prev_button.label, data.prev_button.aria_label)
    ],
    load_wait_label: ''
  })

  return result
}

const save = async (buttonId: string) => {
  loading.value = true
  globalError.value = null

  const userInput: StageData[] = []

  for (let i = 0; i < regularStages.value.length; i++) {
    const formData = (stages.value[i]!.user_input || {}) as StageData
    userInput.push(formData)
  }

  try {
    if (props.objectId) {
      const { redirect_url: redirectUrl } = await editQuickSetup(
        props.quick_setup_id,
        buttonId,
        props.objectId,
        userInput
      )
      window.location.href = redirectUrl
    } else {
      const { redirect_url: redirectUrl } = await saveQuickSetup(
        props.quick_setup_id,
        buttonId,
        userInput
      )
      window.location.href = redirectUrl
    }
  } catch (err) {
    loading.value = false
    handleError(err as RestApiError)
  }
}

const update = (index: number, value: StageData) => {
  if (loading.value) {
    return
  }

  stages.value[index]!.user_input = value
  formData.value[index] = value
}

//
//
// Rendering helpers
//
//
const defineButton = defineButtons(nextStage, prevStage, save)

//
//
// Computed properties to split regular stages from save stage
// and translate them to QuickSetupStageSpec and QuickSetupSaveStageSpec
//
//
const regularStages = computed((): QuickSetupStageSpec[] => {
  return stages.value.slice(0, stages.value.length - 1).map((stg, index) => {
    const item: QuickSetupStageSpec = {
      title: stg.title,
      sub_title: stg.sub_title || null,
      recapContent: renderRecap(stg.recap || []),
      goToThisStage: () => quickSetupHook.goto(index),
      content: renderContent(
        stg.components || [],
        (value) => update(index, value),
        stg.form_spec_errors,
        stg.user_input
      ),
      buttons: stg.buttons!,
      errors: [...asStringArray(stg.errors || []), ...asStringArray(globalError.value || [])],
      loadWaitLabel: stg.load_wait_label || ''
    }
    return item
  })
})

const saveStage = computed((): QuickSetupSaveStageSpec => {
  const stg = stages.value[stages.value.length - 1]!

  return {
    buttons: stg.buttons!,
    errors: [...asStringArray(stg.errors || []), ...asStringArray(globalError.value || [])],
    loadWaitLabel: stg.load_wait_label || ''
  }
})

//
//
// Initialization
//
//

const handleError = (err: RestApiError) => {
  if (err.type === 'general') {
    globalError.value = `An error occurred while trying to proceed to the next step.
The underlying call raised the following error: ${(err as GeneralError).general_error}
Please try again to confirm this is not a one-time occurrence.
Please verify the logs if this error persists.`
  } else {
    stages.value[quickSetupHook.stage.value]!.errors = (err as ValidationError).stage_errors
    stages.value[quickSetupHook.stage.value]!.form_spec_errors = (
      err as ValidationError
    ).formspec_errors
  }
}
const wizardMode: Ref<WizardMode> = usePersistentRef<WizardMode>(
  'quick_setup_wizard_mode',
  props.mode
)

const currentMode = ref<WizardMode>(props.mode)

watch(currentMode, async (mode: WizardMode) => {
  wizardMode.value = mode
  quickSetupHook.setMode(mode)
  if (mode === 'overview' && !loadedAllStages.value) {
    stages.value = await loadAllStages()
  }
})

switch (props.mode) {
  case GUIDED_MODE:
    stages.value = await loadGuidedStages()
    break
  case OVERVIEW_MODE:
    stages.value = await loadAllStages()
    break
}
const quickSetupHook = useWizard(stages.value.length, props.mode)
showQuickSetup.value = true
</script>

<template>
  <ToggleButtonGroup
    v-if="toggleEnabled"
    v-model="currentMode"
    :options="[
      { label: guidedModeLabel, value: GUIDED_MODE },
      { label: overviewModeLabel, value: OVERVIEW_MODE }
    ]"
  />
  <QuickSetup
    v-if="showQuickSetup"
    :loading="loading"
    :regular-stages="regularStages"
    :save-stage="saveStage"
    :current-stage="quickSetupHook.stage.value"
    :mode="quickSetupHook.mode"
  />
</template>

<style scoped></style>
