<script setup lang="ts">
import { computed, ref, onBeforeMount } from 'vue'

import QuickSetupStep from './QuickSetupStep.vue'

import {
  type QuickSetupAppProperties,
  type QuickSetupOverviewRestApiSpec,
  type OverviewSpec,
  type StageSpec,
  type StepData
} from '@/quick_setup_types'

import LoadingIcon from '@/components/LoadingIcon.vue'
// import { ACTIVATE_CHANGES_URL } from '@/constants/ui'
// import { goToUrl } from '@/helpers/url'

const props = defineProps<QuickSetupAppProperties>()
const currentStep = ref(0) //Selected step. We start in step 0
const ready = ref(false) //When data is fully loaded, we set the ready flag
const overviews = ref<OverviewSpec[]>([]) //Overviews data
const stage = ref<StageSpec | null>(null)
const steps = computed(() => overviews.value.length)
const error = ref<string | null>(null)

// Lets store all the user input in this object. The record index is the step number
// When sending data to the Rest API, we send all from index 0..currentStep.
let formularData = ref<{ [key: number]: StepData }>({})

let tmp: StageSpec | null = null //LMP: Just for test purposes (Remove it)

const initializeQuickSetup = async (quickSetupId: string) => {
  try {
    console.log(`Building Quick Setup ${quickSetupId}`)

    const data: QuickSetupOverviewRestApiSpec = { overviews: [], stage: { id: 0, components: [] } }

    error.value = null

    currentStep.value = 0
    overviews.value = data.overviews
    stage.value = data.stage
    ready.value = true

    tmp = data.stage //LMP: Just for test purposes (Remove it)
  } catch (err) {
    console.error(err)
    error.value = 'An error has ocurred'
  }
}

onBeforeMount(() => {
  setTimeout(() => {
    //LMP: Just for test purposes (Remove it)
    initializeQuickSetup(props.quick_setup_id)
  }, 10)
})

const update = (index: number, value: StepData) => {
  formularData.value[index] = value
}

const save = () => {
  console.log('Trigger save data and go to activate changes if success')
}

const nextStep = () => {
  //Validate step. If valid:
  currentStep.value = Math.min(currentStep.value + 1, steps.value - 1)
  stage.value = currentStep.value === 0 ? tmp : null //LMP: Just for test purposes (Remove it)
  //update stage data
}

const prevStep = () => {
  currentStep.value = Math.max(currentStep.value - 1, 0)
  stage.value = currentStep.value === 0 ? tmp : null //LMP: Just for test purposes (Remove it)
  //update stage data
}

/*
Dev notes:
Every step will send the information from steps 0..currentStep to the backend for further validation. 
The backend should send the representation of previous steps and the form for the new one.
*/
</script>

<template>
  <div v-if="error" class="error">{{ error }}</div>
  <ol class="cmk-stepper">
    <div v-if="ready">
      <QuickSetupStep
        v-for="(ovw, index) in overviews"
        :key="index"
        :index="index"
        :selected-step="currentStep"
        :steps="steps"
        :overview="ovw"
        :data="formularData[index] || {}"
        :stage="currentStep == index ? stage : null"
        :next-title="overviews[index + 1]?.title || ''"
        :prev-title="overviews[index - 1]?.title || ''"
        @prev-step="prevStep"
        @next-step="nextStep"
        @save="save"
        @update="update"
      />
    </div>
    <div v-else>
      <LoadingIcon />
    </div>
  </ol>
  <pre>
    {{ formularData }}
  </pre>
</template>

<style scoped>
.cmk-stepper {
  --size: 3rem;
  --spacing: 0.5rem;
}
</style>
