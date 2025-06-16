<!--
Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import {
  computed,
  ref,
  toValue,
  type Ref,
  watch,
  provide,
  readonly,
  onBeforeUnmount,
  onMounted,
  nextTick
} from 'vue'
import QuickSetup from './components/quick-setup/QuickSetup.vue'
import { CmkError, CmkSimpleError, formatError } from '@/lib/error.ts'
import {
  getOverview,
  getAllStages,
  validateAndRecapStage,
  getStageStructure,
  saveOrEditQuickSetup
} from './rest-api/api'
import { formDataKey } from './keys'
import useWizard, { type WizardMode } from './components/quick-setup/useWizard'
import { ActionType, processActionData, renderContent, renderRecap } from './render_utils'
import type {
  QuickSetupSaveStageSpec,
  QuickSetupStageAction,
  QuickSetupStageSpec,
  DetailedError
} from './components/quick-setup/quick_setup_types'
import { type QuickSetupAppProps, type QSStageStore } from './types'
import { asStringArray } from './utils'
import type { StageData } from '@/quick-setup/components/quick-setup/widgets/widget_types'
import ToggleButtonGroup from '@/components/ToggleButtonGroup.vue'
import usePersistentRef from '@/lib/usePersistentRef'
import {
  QuickSetupCompleteActionValidationResponse,
  QuickSetupStageActionErrorValidationResponse,
  type Action,
  type QuickSetupGuidedResponse,
  type QuickSetupStageStructure
} from '@/lib/rest-api-client/quick-setup/response_schemas'
import {
  useBackgroundJobLog,
  type LogUpdate
} from './components/BackgroundJobLog/useBackgroundJobLog'

const GUIDED_MODE = 'guided'
const OVERVIEW_MODE = 'overview'

let guidedModeLabel = ''
let overviewModeLabel = ''

const props = withDefaults(defineProps<QuickSetupAppProps>(), {
  mode: GUIDED_MODE,
  toggle_enabled: false
})

const loadedAllStages = ref(false)
const showQuickSetup = ref(false)
const preventLeaving = ref(false)
const mounted = ref(false)
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
const nextStage = async (actionId: string) => {
  const thisStageNumber = quickSetupHook.stage.value
  const nextStageNumber = quickSetupHook.nextStageIndex()
  const currentStage = stages.value[thisStageNumber]!
  const followingStage = stages.value[nextStageNumber]!

  loading.value = true
  clearErrors()
  currentStage.background_job_log.clear()

  const userInput: StageData[] = []

  for (let i = 0; i <= thisStageNumber; i++) {
    const formData = (toValue(stages.value[i]!.user_input) || {}) as StageData
    userInput.push(formData)
  }

  try {
    const actionResponse = await validateAndRecapStage(
      props.quick_setup_id,
      actionId,
      userInput,
      handleBackgroundJobLogUpdate
    )

    if (actionResponse instanceof QuickSetupStageActionErrorValidationResponse) {
      currentStage.background_job_log.setActiveTasksToError()
      handleValidationError(actionResponse, thisStageNumber)
      handleBackgroundJobError(actionResponse)
      loading.value = false
      return
    }

    currentStage.form_spec_errors = actionResponse.validation_errors?.formspec_errors || {}
    currentStage.errors = actionResponse.validation_errors?.stage_errors || []
    currentStage.recap = actionResponse.stage_recap
  } catch (err: unknown) {
    currentStage.background_job_log.setActiveTasksToError()
    handleExceptionError(err)
    loading.value = false
    return
  }

  followingStage.background_job_log.clear()
  //If we have not finished the quick setup yet, but still on the regular steps
  if (nextStageNumber < numberOfStages.value - 1) {
    let nextStageStructure: QuickSetupStageStructure
    try {
      nextStageStructure = await getStageStructure(
        props.quick_setup_id,
        nextStageNumber,
        props.object_id
      )
    } catch (err: unknown) {
      handleExceptionError(err)
    }

    const acts: QuickSetupStageAction[] = followingStage.actions || []

    acts.length = 0

    for (const action of nextStageStructure!.actions) {
      // eslint-disable-next-line @typescript-eslint/no-misused-promises
      acts.push(processActionData(ActionType.Next, action, nextStage))
    }

    if (nextStageStructure!.prev_button) {
      acts.push(
        processActionData(
          ActionType.Prev,
          {
            id: 'prev',
            button: nextStageStructure!.prev_button,
            load_wait_label: ''
          },
          prevStage
        )
      )
    }

    stages.value[nextStageNumber] = {
      ...followingStage,
      components: nextStageStructure!.components,
      recap: [],
      form_spec_errors: {},
      errors: [],
      actions: acts
    }
  }

  quickSetupHook.next()
  loading.value = false
}

const prevStage = () => {
  const prevStage = quickSetupHook.previousStageIndex()
  stages.value[prevStage]!.background_job_log.clear()
  clearErrors()
  quickSetupHook.prev()
}

const loadAllStages = async (): Promise<QSStageStore[]> => {
  const data = await getAllStages(props.quick_setup_id, props.object_id)
  const result: QSStageStore[] = []

  guidedModeLabel = data.guided_mode_string
  overviewModeLabel = data.overview_mode_string

  for (let stageIndex = 0; stageIndex < data.stages.length; stageIndex++) {
    const stage = data.stages[stageIndex]!

    const acts: QuickSetupStageAction[] = []
    if (stageIndex !== data.stages.length - 1) {
      for (const action of stage.actions) {
        // eslint-disable-next-line @typescript-eslint/no-misused-promises
        acts.push(processActionData(ActionType.Next, action, nextStage))
      }
    }
    if (stageIndex !== 0 && stage?.prev_button) {
      acts.push(
        processActionData(
          ActionType.Prev,
          {
            id: 'prev',
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
      actions: acts,
      background_job_log: useBackgroundJobLog(true)
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
    // eslint-disable-next-line @typescript-eslint/no-misused-promises
    actions: [...data.actions.map((action) => processActionData(ActionType.Save, action, save))],
    background_job_log: useBackgroundJobLog(true)
  })
  loadedAllStages.value = true
  return result
}

const loadGuidedStages = async (): Promise<QSStageStore[]> => {
  const data: QuickSetupGuidedResponse = await getOverview(props.quick_setup_id, props.object_id)
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
      for (const action of data.stage.actions) {
        // eslint-disable-next-line @typescript-eslint/no-misused-promises
        acts.push(processActionData(ActionType.Next, action, nextStage))
      }
    }

    result.push({
      title: overview.title,
      sub_title: overview.sub_title || null,
      components: isFirst ? data.stage.components : [],
      recap: [],
      form_spec_errors: {},
      errors: [],
      user_input: ref(userInput),
      actions: acts,
      background_job_log: useBackgroundJobLog(true)
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
      // eslint-disable-next-line @typescript-eslint/no-misused-promises
      ...data.actions.map((action: Action) => processActionData(ActionType.Save, action, save)),
      processActionData(
        ActionType.Prev,
        {
          id: 'prev',
          button: data.prev_button!,
          load_wait_label: ''
        },
        prevStage
      )
    ],
    background_job_log: useBackgroundJobLog(true)
  })

  return result
}

const save = async (buttonId: string) => {
  const thisStageNumber = quickSetupHook.stage.value
  const currentStage = stages.value[thisStageNumber]!

  loading.value = true
  currentStage.background_job_log.clear()
  clearErrors()

  const userInput: StageData[] = []

  for (let i = 0; i < regularStages.value.length; i++) {
    const formData = (stages.value[i]!.user_input || {}) as StageData
    userInput.push(formData)
  }

  try {
    handlePreventLeaving(false)
    const data = await saveOrEditQuickSetup(
      props.quick_setup_id,
      buttonId,
      userInput,
      props.object_id,
      handleBackgroundJobLogUpdate
    )
    loading.value = true

    if (data instanceof QuickSetupCompleteActionValidationResponse) {
      currentStage.background_job_log.setActiveTasksToError()
      handleAllStagesValidationError(data)
      handleBackgroundJobError(data)
      return
    } else {
      window.location.href = data.redirect_url
    }
  } catch (err: unknown) {
    currentStage.background_job_log.setActiveTasksToError()
    loading.value = false
    handleExceptionError(err)
  } finally {
    loading.value = false
  }
}

const update = (index: number, value: StageData) => {
  if (loading.value) {
    return
  }

  const clonedValue = structuredClone(value)

  stages.value[index]!.user_input = clonedValue
  formData.value[index] = clonedValue

  if (mounted.value) {
    handlePreventLeaving(true)
  }
}

const clearErrors = () => {
  globalError.value = null
  for (const stage of stages.value) {
    stage.errors = []
    stage.form_spec_errors = {}
  }
}

const handlePreventLeaving = (prevent: boolean) => {
  preventLeaving.value = prevent
  if (prevent) {
    window.addEventListener('beforeunload', handleBrowserDialog)
  } else {
    window.removeEventListener('beforeunload', handleBrowserDialog)
  }
}

const handleBrowserDialog = (event: BeforeUnloadEvent) => {
  if (preventLeaving.value) {
    event.preventDefault()
    event.returnValue = ''
  }
}

onMounted(async () => {
  await nextTick(() => {
    mounted.value = true
  })
})

onBeforeUnmount(() => {
  handlePreventLeaving(false)
})

//
//
// Computed properties to split regular stages from save stage
// and translate them to QuickSetupStageSpec and QuickSetupSaveStageSpec
//
//
const regularStages = computed((): QuickSetupStageSpec[] => {
  return stages.value.slice(0, stages.value.length - 1).map((stg, index: number) => {
    const item: QuickSetupStageSpec = {
      title: stg.title,
      sub_title: stg.sub_title || null,
      recapContent: renderRecap(stg.recap || []),
      goToThisStage: () => {
        stages.value[index]!.background_job_log.clear()
        clearErrors()
        quickSetupHook.goto(index)
      },
      content: renderContent(
        stg.components || [],
        (value) => update(index, value),
        stg.background_job_log.entries,
        stg.background_job_log.isRunning,
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
    actions: [...stg.actions.values()],
    content: renderContent(
      stg.components || [],
      () => {},
      stg.background_job_log.entries,
      stg.background_job_log.isRunning,
      stg.form_spec_errors,
      stg.user_input
    )
  }
})

//
//
// Initialization
//
//

const handleValidationError = (
  actionResponse: QuickSetupStageActionErrorValidationResponse,
  thisStageNumber: number
) => {
  stages.value[thisStageNumber]!.form_spec_errors =
    actionResponse.validation_errors?.formspec_errors || {}
  stages.value[thisStageNumber]!.errors = actionResponse.validation_errors?.stage_errors || []
}

const handleAllStagesValidationError = (data: QuickSetupCompleteActionValidationResponse) => {
  const errs = data.all_stage_errors || []
  for (const stageError of errs) {
    const stageIndex =
      typeof stageError.stage_index !== 'undefined' && stageError.stage_index !== null
        ? stageError.stage_index
        : stages.value.length - 1

    stages.value[stageIndex]!.errors = stageError.stage_errors
    stages.value[stageIndex]!.form_spec_errors = stageError.formspec_errors
  }
}

const handleBackgroundJobError = (
  data: QuickSetupStageActionErrorValidationResponse | QuickSetupCompleteActionValidationResponse
) => {
  if (data.background_job_exception) {
    globalError.value = {
      type: 'DetailedError',
      message: data.background_job_exception.message,
      details: data.background_job_exception.traceback
    }
  }
}

const handleExceptionError = (err: unknown) => {
  if (err instanceof CmkSimpleError) {
    globalError.value = err.message
  } else if (err instanceof CmkError) {
    globalError.value = {
      type: 'DetailedError',
      message: err.message,
      details: formatError(err)
    }
  } else if (err instanceof Error) {
    const message =
      'An unknown error occurred. Refresh the page to try again. If the problem persists, reach out to the Checkmk support.'
    globalError.value = {
      type: 'DetailedError',
      message: message,
      details: formatError(err)
    }
  } else {
    throw Error('Can not handle error')
  }
}

const handleBackgroundJobLogUpdate = (log: LogUpdate | null) => {
  stages.value[quickSetupHook.stage.value]!.background_job_log.update(log)
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

const hideWaitIcon = computed(
  (): boolean => stages.value[quickSetupHook.stage.value]!.background_job_log.entries.length > 0
)

const quickSetupHook = useWizard(stages.value.length, props.mode)

showQuickSetup.value = true
</script>

<template>
  <ToggleButtonGroup
    v-if="toggle_enabled"
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
    :hide-wait-icon="hideWaitIcon"
  />
</template>

<style scoped></style>
