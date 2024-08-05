<script setup lang="ts">
import { computed, ref, onBeforeMount, defineAsyncComponent } from 'vue'

import LoadingIcon from '@/components/LoadingIcon.vue'

const AlertBox = defineAsyncComponent(() => import('@/components/AlertBox.vue'))
const QuickSetupStep = defineAsyncComponent(() => import('./QuickSetupStep.vue'))

import { type QuickSetupSpec, type QuickSetupStageSpec, type StageData } from './quick_setup_types'
import {
  type QSInitializationResponse,
  type ValidationError,
  type GeneralError,
  type RestApiError,
  type QSStageResponse
} from './rest_api_types'
import { getOverview, validateStep } from './rest_api'

const props = defineProps<QuickSetupSpec>()
const currentStep = ref(0) //Selected step. We start in step 0
const ready = ref(false) //When data is fully loaded, we set the ready flag
const stage = ref<QuickSetupStageSpec[]>([]) //New Stage data
const steps = computed(() => stage.value.length) //Total steps
const globalError = ref<string | null>(null) //Main error message
const loading = ref(false)
const buttonCompleteLabel = ref('Save')

// Lets store all the user input in this object. The record index is the step number
// When sending data to the Rest API, we send all from index 0..currentStep.
let formData = ref<{ [key: number]: StageData }>({})

const initializeStagesData = (skeleton: QSInitializationResponse) => {
  for (let index = 0; index < skeleton.overviews.length; index++) {
    const isFirst = index === 0
    const overview = skeleton.overviews[index]!

    stage.value.push({
      title: overview.title,
      sub_title: overview.sub_title || null,
      next_button_label: isFirst ? skeleton.stage.next_stage_structure.button_label || null : null,
      components: isFirst ? skeleton.stage.next_stage_structure.components : [],
      recap: [],
      form_spec_errors: {},
      other_errors: [],
      user_input: ref<StageData>({})
    })
  }
}

const initializeQuickSetup = async (quickSetupId: string) => {
  try {
    const data = await getOverview(quickSetupId)
    initializeStagesData(data)
    buttonCompleteLabel.value = data.button_complete_label
    globalError.value = null
    currentStep.value = 0
  } catch (err) {
    globalError.value = err as string
  } finally {
    ready.value = true
  }
}

onBeforeMount(() => {
  initializeQuickSetup(props.quick_setup_id)
})

const update = (index: number, value: StageData) => {
  stage.value[index]!.user_input = value
  formData.value[index] = value
}

const save = async () => {
  console.log('Trigger save data and go to activate changes if success')

  //This will be changed in the next commit
  await nextStep()
}

const handleError = (err: RestApiError) => {
  if (err.type === 'general') {
    globalError.value = (err as GeneralError).general_error
  } else {
    stage.value[currentStep.value]!.form_spec_errors = (err as ValidationError).formspec_errors
  }
}

const nextStep = async () => {
  loading.value = true
  globalError.value = null

  const thisStage = currentStep.value
  const nextStage = thisStage + 1

  const userInput: StageData[] = []

  for (let i = 0; i <= thisStage; i++) {
    const formData = (stage.value[i]!.user_input || {}) as StageData
    userInput.push(formData)
  }

  let result: QSStageResponse | null = null

  try {
    result = await validateStep(props.quick_setup_id, userInput)
  } catch (err) {
    handleError(err as RestApiError)
  }

  loading.value = false
  if (!result) {
    return
  }

  //Clear form_spec_errors and other_errors from thisStage
  stage.value[thisStage]!.form_spec_errors = {}
  stage.value[thisStage]!.other_errors = []
  stage.value[thisStage]!.recap = result.stage_recap

  //If we have not finished the quick setup yet, update data and display next stage
  if (nextStage < steps.value) {
    stage.value[nextStage] = {
      ...stage.value[nextStage]!,
      components: result.next_stage_structure.components,
      next_button_label: result.next_stage_structure.button_label || '',
      recap: [],
      form_spec_errors: {},
      other_errors: []
    }

    currentStep.value = nextStage
  } else {
    //Otherwise, we are done. Display last info and prepare to launch
  }
}

const prevStep = () => {
  currentStep.value = Math.max(currentStep.value - 1, 0)
}
</script>

<template>
  <AlertBox v-if="globalError" variant="error">{{ globalError }}</AlertBox>
  <ol v-if="ready" class="cmk-stepper">
    <QuickSetupStep
      v-for="(stg, index) in stage"
      :key="index"
      :index="index"
      :selected-step="currentStep"
      :steps="steps"
      :loading="loading"
      :spec="stg"
      @prev-step="prevStep"
      @next-step="nextStep"
      @save="save"
      @update="update"
    />
  </ol>
  <LoadingIcon v-else />
</template>

<style scoped>
.cmk-stepper {
  --size: 3rem;
  --spacing: 0.5rem;
}
</style>
