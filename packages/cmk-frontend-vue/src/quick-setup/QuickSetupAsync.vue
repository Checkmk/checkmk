<!--
Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { computed, ref, toValue, type Ref, watch, provide, readonly } from 'vue'
import QuickSetup from './components/quick-setup/QuickSetup.vue'
import { formatError } from '@/components/CmkError'
import {
  saveQuickSetup,
  getOverview,
  validateStage,
  getAllStages,
  editQuickSetup
} from './rest-api/api'
import { formDataKey } from './keys'
import useWizard, { type WizardMode } from './components/quick-setup/useWizard'
import type { ComponentSpec } from './components/quick-setup/widgets/widget_types'
import { ActionType, processActionData, renderContent, renderRecap } from './render_utils'
import type {
  QuickSetupSaveStageSpec,
  QuickSetupStageAction,
  QuickSetupStageSpec,
  DetailedError
} from './components/quick-setup/quick_setup_types'
import { type QuickSetupAppProps } from './types'
import type { QSInitializationResponse, QSStageResponse } from './rest-api/types'
import { isValidationError, isAllStagesValidationError } from './rest-api/types'
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
  actions: QuickSetupStageAction[]
}

const GUIDED_MODE = 'guided'
const OVERVIEW_MODE = 'overview'

let guidedModeLabel = ''
let overviewModeLabel = ''

const props = withDefaults(defineProps<QuickSetupAppProps>(), {
  mode: GUIDED_MODE,
  toggleEnabled: false
})

const loadedAllStages = ref(false)
const showQuickSetup = ref(false)
const preventLeaving = ref(false)
const stages = ref<QSStageStore[]>([])
const globalError = ref<string | DetailedError | null>(null) //Main error message
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
const nextStage = async (actionId: string | null = null) => {
  loading.value = true
  globalError.value = null

  const thisStageNumber = quickSetupHook.stage.value
  const nextStageNumber = quickSetupHook.stage.value + 1

  const userInput: StageData[] = []

  for (let i = 0; i <= thisStageNumber; i++) {
    const formData = (toValue(stages.value[i]!.user_input) || {}) as StageData
    userInput.push(formData)
  }

  let result: QSStageResponse | null = null

  try {
    result = await validateStage(props.quick_setup_id, userInput, actionId, props.objectId)
  } catch (err: unknown) {
    handleError(err)
  }

  loading.value = false
  if (!result) {
    return
  }

  //Clear form_spec_errors and other_errors from thisStageNumber
  stages.value[thisStageNumber]!.form_spec_errors = {}
  stages.value[thisStageNumber]!.errors = []

  stages.value[thisStageNumber]!.recap = result.stage_recap

  //If we have not finished the quick setup yet, but still on the, regular step
  if (nextStageNumber < numberOfStages.value - 1) {
    const acts: QuickSetupStageAction[] = stages.value[nextStageNumber]?.actions || []

    acts.length = 0

    for (const action of result.next_stage_structure.actions) {
      acts.push(processActionData(ActionType.Next, action, nextStage))
    }

    if (result.next_stage_structure.prev_button) {
      acts.push(
        processActionData(
          ActionType.Prev,
          {
            button: result.next_stage_structure.prev_button,
            load_wait_label: ''
          },
          prevStage
        )
      )
    }

    stages.value[nextStageNumber] = {
      ...stages.value[nextStageNumber]!,
      components: result.next_stage_structure.components,
      recap: [],
      form_spec_errors: {},
      errors: [],
      actions: acts
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

    const acts: QuickSetupStageAction[] = []
    if (stageIndex !== data.stages.length - 1) {
      for (const action of stage.actions) {
        acts.push(processActionData(ActionType.Next, action, nextStage))
      }
    }
    if (stageIndex !== 0 && stage?.prev_button) {
      acts.push(
        processActionData(
          ActionType.Prev,
          {
            button: stage.prev_button,
            load_wait_label: ''
          },
          prevStage
        )
      )
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
      actions: acts
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
    actions: [...data.actions.map((action) => processActionData(ActionType.Save, action, save))]
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

    const acts: QuickSetupStageAction[] = []

    if (isFirst) {
      for (const action of data.stage.next_stage_structure.actions) {
        acts.push(processActionData(ActionType.Next, action, nextStage))
      }
    }

    result.push({
      title: overview.title,
      sub_title: overview.sub_title || null,
      components: isFirst ? data.stage.next_stage_structure.components : [],
      recap: [],
      form_spec_errors: {},
      errors: [],
      user_input: ref(userInput),
      actions: acts
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
    actions: [
      ...data.actions.map((action) => processActionData(ActionType.Save, action, save)),
      processActionData(
        ActionType.Prev,
        {
          button: data.prev_button,
          load_wait_label: ''
        },
        prevStage
      )
    ]
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

    stages.value[i]!.form_spec_errors = {}
    stages.value[i]!.errors = []
  }

  try {
    if (props.objectId) {
      preventLeaving.value = false
      const { redirect_url: redirectUrl } = await editQuickSetup(
        props.quick_setup_id,
        buttonId,
        props.objectId,
        userInput
      )
      window.location.href = redirectUrl
    } else {
      preventLeaving.value = false
      const { redirect_url: redirectUrl } = await saveQuickSetup(
        props.quick_setup_id,
        buttonId,
        userInput
      )
      window.location.href = redirectUrl
    }
  } catch (err: unknown) {
    loading.value = false
    handleError(err)
  }
}

const update = (index: number, value: StageData) => {
  if (loading.value) {
    return
  }

  stages.value[index]!.user_input = value
  formData.value[index] = value
  preventLeaving.value = true
}

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
      errors: [...asStringArray(stg.errors || []), ...asStringArray(globalError.value || [])],
      actions: [...stg.actions.values()]
    }
    return item
  })
})

const saveStage = computed((): QuickSetupSaveStageSpec => {
  const stg = stages.value[stages.value.length - 1]!

  return {
    errors: [...asStringArray(stg.errors || []), ...asStringArray(globalError.value || [])],
    actions: [...stg.actions.values()]
  }
})

//
//
// Initialization
//
//

const handleError = (err: unknown) => {
  if (isAllStagesValidationError(err)) {
    const errs = err

    for (const stageError of errs.all_stage_errors || []) {
      const stageIndex =
        typeof stageError.stage_index !== 'undefined' && stageError.stage_index !== null
          ? stageError.stage_index
          : stages.value.length - 1

      stages.value[stageIndex]!.errors = stageError.stage_errors
      stages.value[stageIndex]!.form_spec_errors = stageError.formspec_errors
    }
  } else if (isValidationError(err)) {
    stages.value[quickSetupHook.stage.value]!.errors = err.stage_errors || []
    stages.value[quickSetupHook.stage.value]!.form_spec_errors = err.formspec_errors || {}
  } else if (err instanceof Error) {
    const message =
      'An error occurred while trying to proceed to the next step. Please try again to confirm this is not a one-time occurrence. Please verify the logs if this error persists.'
    globalError.value = {
      type: 'DetailedError',
      message: message,
      details: formatError(err)
    }
  } else {
    throw Error('Can not handle error')
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
preventLeaving.value = false
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
    :prevent-leaving="preventLeaving"
  />
</template>

<style scoped></style>
