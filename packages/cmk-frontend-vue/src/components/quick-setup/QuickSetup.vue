<script setup lang="ts">
import { computed, ref, onBeforeMount } from 'vue'

import LoadingIcon from '@/components/common/LoadingIcon.vue'
import Button from './element/IconButton.vue'
import QuickSetupStage from './QuickSetupStage.vue'
import { type QuickSetupSpec, type QuickSetupStageSpec, type StageData } from './quick_setup_types'
import {
  type QSInitializationResponse,
  type ValidationError,
  type GeneralError,
  type RestApiError,
  type QSStageResponse
} from './rest_api_types'

import { completeQuickSetup, getOverview, validateStage } from './rest_api'

const props = defineProps<QuickSetupSpec>()
const currentStage = ref(0) //Selected stage. We start in stage 0
const ready = ref(false) //When data is fully loaded, we set the ready flag
const stages = ref<QuickSetupStageSpec[]>([]) //New Stage data
const numberOfStages = computed(() => stages.value.length) //Number of stages
const globalError = ref<string | null>(null) //Main error message
const loading = ref(false)
const buttonCompleteLabel = ref('Save')

// Lets store all the user input in this object. The record index is the stage number
// When sending data to the Rest API, we send all from index 0..currentStage.
let formData = ref<{ [key: number]: StageData }>({})

const initializeStagesData = (skeleton: QSInitializationResponse) => {
  for (let index = 0; index < skeleton.overviews.length; index++) {
    const isFirst = index === 0
    const overview = skeleton.overviews[index]!

    stages.value.push({
      title: overview.title,
      sub_title: overview.sub_title || null,
      next_button_label: isFirst ? skeleton.stage.next_stage_structure.button_label || null : null,
      components: isFirst ? skeleton.stage.next_stage_structure.components : [],
      recap: [],
      form_spec_errors: {},
      stage_errors: [],
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
    currentStage.value = 0
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
  stages.value[index]!.user_input = value
  formData.value[index] = value
}

const handleError = (err: RestApiError) => {
  if (err.type === 'general') {
    globalError.value = (err as GeneralError).general_error
  } else {
    stages.value[currentStage.value]!.form_spec_errors = (err as ValidationError).formspec_errors
    stages.value[currentStage.value]!.stage_errors = (err as ValidationError).stage_errors
  }
}

const nextStage = async () => {
  loading.value = true
  globalError.value = null

  const thisStage = currentStage.value
  const nextStage = thisStage + 1

  const userInput: StageData[] = []

  for (let i = 0; i <= thisStage; i++) {
    const formData = (stages.value[i]!.user_input || {}) as StageData
    userInput.push(formData)
  }

  let result: QSStageResponse | null = null

  try {
    result = await validateStage(props.quick_setup_id, userInput)
  } catch (err) {
    handleError(err as RestApiError)
  }

  loading.value = false
  if (!result) {
    return
  }

  //Clear form_spec_errors and other_errors from thisStage
  stages.value[thisStage]!.form_spec_errors = {}
  stages.value[thisStage]!.other_errors = []
  stages.value[thisStage]!.stage_errors = []
  stages.value[thisStage]!.recap = result.stage_recap

  //If we have not finished the quick setup yet, update data and display next stage
  if (nextStage < numberOfStages.value) {
    stages.value[nextStage] = {
      ...stages.value[nextStage]!,
      components: result.next_stage_structure.components,
      next_button_label: result.next_stage_structure.button_label || '',
      recap: [],
      form_spec_errors: {},
      stage_errors: []
    }
  }

  currentStage.value = nextStage
}

const prevStage = () => {
  globalError.value = null
  currentStage.value = Math.max(currentStage.value - 1, 0)
}

const save = async () => {
  loading.value = true
  globalError.value = null

  const userInput: StageData[] = []

  for (let i = 0; i < numberOfStages.value; i++) {
    const formData = (stages.value[i]!.user_input || {}) as StageData
    userInput.push(formData)
  }

  try {
    const { redirect_url: redirectUrl } = await completeQuickSetup(props.quick_setup_id, userInput)
    window.location.href = redirectUrl
  } catch (err) {
    handleError(err as RestApiError)
  }
}
</script>

<template>
  <ol v-if="ready" class="quick-setup">
    <QuickSetupStage
      v-for="(stg, index) in stages"
      :key="index"
      :index="index"
      :selected-stage="currentStage"
      :number-of-stages="numberOfStages"
      :loading="loading"
      :spec="stg"
      :other_errors="globalError || []"
      :save_button_label="buttonCompleteLabel"
      @prev-stage="prevStage"
      @next-stage="nextStage"
      @save="save"
      @update="update"
    />
  </ol>
  <LoadingIcon v-else />
  <div v-if="currentStage >= numberOfStages" class="qs-main__action">
    <div v-if="loading">
      <p class="qs-main__loading"><LoadingIcon :height="16" />Please wait...</p>
    </div>
    <div v-else>
      <Button :label="buttonCompleteLabel" variant="save" @click="save" />
      <Button style="padding-left: 1rem" label="Back" variant="prev" @click="prevStage" />
    </div>
  </div>
</template>

<style scoped>
.quick-setup {
  counter-reset: stage-index;
  --size: 3rem;
  --spacing: 0.5rem;
}

.qs-main__action {
  padding-top: 1rem;
  padding-left: 7.5rem;
  position: relative;
}

.qs-stage__loading {
  padding-left: 1rem;
}
</style>
