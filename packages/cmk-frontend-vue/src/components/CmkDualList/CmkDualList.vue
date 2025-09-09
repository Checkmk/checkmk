<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import type { Validator } from 'cmk-shared-typing/typescript/vue_formspec_components'
import { computed, shallowRef } from 'vue'

import usei18n from '@/lib/i18n'

import CmkButton from '@/components/CmkButton.vue'
import FormValidation from '@/components/user-input/CmkInlineValidation.vue'

import { type ValidationMessages, useValidation } from '@/form/components/utils/validation'

import CmkSearchableList from './CmkSearchableList.vue'
import type { DualListElement } from './index.ts'

const props = defineProps<{
  elements: DualListElement[]
  title: string

  validators: Validator[]
  backendValidation: ValidationMessages
}>()

const data = defineModel<DualListElement[]>('data', { required: true })

const unselectedListRef = shallowRef<InstanceType<typeof CmkSearchableList>>()
const selectedListRef = shallowRef<InstanceType<typeof CmkSearchableList>>()

const { _t } = usei18n()

const [validation] = useValidation<DualListElement[]>(
  data,
  props.validators,
  () => props.backendValidation
)

const unselectedItems = computed<DualListElement[]>(() => {
  const selectedNames = new Set(data.value.map((e) => e.name))
  return props.elements.filter((el) => !selectedNames.has(el.name))
})

const selectedItems = computed<DualListElement[]>(() => {
  const selectedNames = new Set(data.value.map((e) => e.name))
  return props.elements.filter((el) => selectedNames.has(el.name))
})

function updateSelected(newSelected: DualListElement[]) {
  unselectedListRef.value?.clearSelection()
  selectedListRef.value?.clearSelection()
  data.value = newSelected
}

function addSelected() {
  const itemsToAdd = unselectedListRef.value?.getSelected() || []
  if (itemsToAdd.length > 0) {
    updateSelected([...data.value, ...itemsToAdd])
  }
}

function removeSelected() {
  const itemsToRemove = selectedListRef.value?.getSelected() || []
  if (itemsToRemove.length > 0) {
    const newSelected = data.value.filter(
      (entry) => !itemsToRemove.some((e) => e.name === entry.name)
    )
    updateSelected(newSelected)
  }
}

function addAllFiltered() {
  const itemsToAdd = unselectedListRef.value?.getVisibleItems() || []
  const newSelected = [...data.value, ...itemsToAdd]
  updateSelected(newSelected)
}

function removeAllFiltered() {
  const itemsToRemove = selectedListRef.value?.getVisibleItems() || []
  const newSelected = data.value.filter(
    (entry) => !itemsToRemove.some((e) => e.name === entry.name)
  )
  updateSelected(newSelected)
}

function handleDoubleClickToAddItem(element: DualListElement) {
  updateSelected([...data.value, element])
}

function handleDoubleClickToRemoveItem(element: DualListElement) {
  const newSelected = data.value.filter((e) => e.name !== element.name)
  updateSelected(newSelected)
}

const elementsTitleMaxLength = computed(() => {
  return props.elements.reduce((max, element) => Math.max(max, element.title.length), 3)
})

const elementCounter = computed(() => props.elements.length)
</script>

<template>
  <div class="cmk-dual-list-container" role="group" :aria-label="title">
    <div class="cmk-dual-list-body">
      <div class="cmk-dual-list-single-list">
        <CmkSearchableList
          ref="unselectedListRef"
          :elements="unselectedItems"
          :title="_t('Available options')"
          :count-elements="elementCounter"
          :length-elements="elementsTitleMaxLength"
          @element:dblclick="handleDoubleClickToAddItem"
        />
      </div>

      <div class="cmk-dual-list-action-buttons">
        <div class="cmk-dual-list-action-button">
          <CmkButton
            :disabled="!unselectedListRef?.getSelected().length"
            :aria-label="_t('Add >')"
            @click="addSelected"
          >
            &gt;
          </CmkButton>
        </div>
        <div class="cmk-dual-list-action-button">
          <CmkButton
            :disabled="!unselectedListRef?.getVisibleItems().length"
            :aria-label="_t('Add all >>')"
            @click="addAllFiltered"
          >
            &gt;&gt;&gt;
          </CmkButton>
        </div>
        <div class="cmk-dual-list-action-button">
          <CmkButton
            :disabled="!selectedListRef?.getVisibleItems().length"
            :aria-label="_t('<< Remove all')"
            @click="removeAllFiltered"
          >
            &lt;&lt;&lt;
          </CmkButton>
        </div>
        <div class="cmk-dual-list-action-button">
          <CmkButton
            :disabled="!selectedListRef?.getSelected().length"
            :aria-label="_t('< Remove')"
            @click="removeSelected"
          >
            &lt;
          </CmkButton>
        </div>
      </div>

      <div class="cmk-dual-list-single-list">
        <CmkSearchableList
          ref="selectedListRef"
          :elements="selectedItems"
          :title="_t('Selected options')"
          :count-elements="elementCounter"
          :length-elements="elementsTitleMaxLength"
          @element:dblclick="handleDoubleClickToRemoveItem"
        />
      </div>
    </div>
  </div>
  <FormValidation :validation="validation" />
</template>

<style scoped>
/* stylelint-disable-next-line checkmk/vue-bem-naming-convention */
.cmk-dual-list-container {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

/* stylelint-disable-next-line checkmk/vue-bem-naming-convention */
.cmk-dual-list-body {
  display: flex;
  gap: 1rem;
  align-items: center;
}

/* stylelint-disable-next-line checkmk/vue-bem-naming-convention */
.cmk-dual-list-single-list {
  flex: 1;
}

/* stylelint-disable-next-line checkmk/vue-bem-naming-convention */
.cmk-dual-list-action-buttons {
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
  border-radius: 10px;
  width: 100%;
  max-width: 51px;
}

/* stylelint-disable-next-line checkmk/vue-bem-naming-convention */
.cmk-dual-list-action-button {
  margin: 5px;
  width: 100%;
}

/* stylelint-disable-next-line checkmk/vue-bem-naming-convention */
.cmk-dual-list-action-button button {
  width: 100%;
}
</style>
