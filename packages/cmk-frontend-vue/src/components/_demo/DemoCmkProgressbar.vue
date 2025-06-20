<!--
Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->

<script setup lang="ts">
import CmkProgressbar from '@/components/CmkProgressbar.vue'
import CmkButton from '../CmkButton.vue'
import CmkDropdown from '../CmkDropdown.vue'
import { nextTick, onMounted, ref } from 'vue'
defineProps<{ screenshotMode: boolean }>()
const value = defineModel<number>('value', { default: 30 })
const max = defineModel<number>('max', { default: 100 })
const labelUnit = defineModel<string>('label-unit', { default: '%' })

function randomValue(): void {
  value.value = Math.round(Math.random() * max.value)
}

const infiniteSelected = ref<'default' | 'infinite'>('default')
const showLabelSelected = ref<'yes' | 'no'>('no')
const labelMaxSelected = ref<'yes' | 'no'>('yes')
const sizeSelected = ref<'small' | 'medium' | 'large'>('medium')

onMounted(() => {
  void nextTick(() => {
    randomValue()
  })
})
</script>

<template>
  <label>Progress-Type: </label>
  <CmkDropdown
    v-model:selected-option="infiniteSelected"
    :options="{
      type: 'fixed',
      suggestions: [
        { name: 'default', title: 'default' },
        { name: 'infinite', title: 'infinite' }
      ]
    }"
    input-hint="some input hint"
    no-results-hint="no results hint"
    required-text="required"
    label="some label"
  />
  <br /><br /><br />
  <label>Size: </label>
  <CmkDropdown
    v-model:selected-option="sizeSelected"
    :options="{
      type: 'fixed',
      suggestions: [
        { name: 'small', title: 'small' },
        { name: 'medium', title: 'medium' },
        { name: 'large', title: 'large' }
      ]
    }"
    input-hint="some input hint"
    no-results-hint="no results hint"
    required-text="required"
    label="some label"
  />
  <br /><br /><br />

  <div v-if="infiniteSelected === 'default'">
    <label>Show label: </label>
    <CmkDropdown
      v-model:selected-option="showLabelSelected"
      :options="{
        type: 'fixed',
        suggestions: [
          { name: 'yes', title: 'yes' },
          { name: 'no', title: 'no' }
        ]
      }"
      input-hint="some input hint"
      no-results-hint="no results hint"
      required-text="required"
      label="some label"
    />
    <br /><br /><br />

    <div v-if="showLabelSelected === 'yes'">
      <label>Show max value in label: </label>
      <CmkDropdown
        v-model:selected-option="labelMaxSelected"
        :options="{
          type: 'fixed',
          suggestions: [
            { name: 'yes', title: 'yes' },
            { name: 'no', title: 'no' }
          ]
        }"
        input-hint="some input hint"
        no-results-hint="no results hint"
        required-text="required"
        label="some label"
      />
      <br /><br /><br />

      <label>Label unit: </label>
      <input v-model="labelUnit" />
      <br /><br /><br />
    </div>

    <label>Max-Value: </label>
    <input v-model="max" type="number" />
    <br /><br /><br />

    <CmkButton @click="randomValue">Generate random value (cur. {{ value }})</CmkButton>
    <br /><br /><br />
  </div>
  <div class="progress-bar">
    <CmkProgressbar
      :value="value"
      :size="sizeSelected"
      :max="infiniteSelected === 'infinite' ? 'unknown' : max"
      :label="
        infiniteSelected === 'infinite' || showLabelSelected === 'no'
          ? undefined
          : {
              showTotal: labelMaxSelected === 'yes',
              unit: labelUnit
            }
      "
    ></CmkProgressbar>
  </div>
</template>

<style scoped>
.progress-bar {
  width: 100%;
  height: 20px;
}
</style>
