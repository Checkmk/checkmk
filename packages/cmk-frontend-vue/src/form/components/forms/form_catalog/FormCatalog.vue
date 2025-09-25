<!--
Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import type {
  Catalog,
  Topic,
  TopicElement,
  TopicGroup
} from 'cmk-shared-typing/typescript/vue_formspec_components'
import { ref } from 'vue'

import { immediateWatch } from '@/lib/watch'

import CmkIcon from '@/components/CmkIcon'
import CmkSpace from '@/components/CmkSpace.vue'

import TopicGrouped from '@/form/components/forms/form_catalog/TopicGrouped.vue'
import TopicUngrouped from '@/form/components/forms/form_catalog/TopicUngrouped.vue'
import { type ValidationMessages, groupNestedValidations } from '@/form/components/utils/validation'

const props = defineProps<{
  spec: Catalog
  backendValidation: ValidationMessages
}>()

const data = defineModel<Record<string, Record<string, unknown>>>('data', { required: true })

const hiddenTopics = ref<Record<string, boolean>>({})

immediateWatch(
  () => props.spec.elements,
  () => {
    hiddenTopics.value = {}
  }
)

const elementValidation = ref<Record<string, ValidationMessages>>({})
immediateWatch(
  () => props.backendValidation,
  (newValidation: ValidationMessages) => {
    const [, nestedValidation] = groupNestedValidations(props.spec.elements, newValidation)
    elementValidation.value = nestedValidation
  }
)

function toggleTopic(topic: Topic) {
  hiddenTopics.value[topic.name] = !hiddenTopics.value[topic.name]
}

function isGroupedTopic(topic: Topic): boolean {
  if (topic.elements.length === 0) {
    return false
  }
  return topic.elements[0]!.type === 'topic_group'
}
</script>

<template>
  <span>
    <template v-for="topic in props.spec.elements" :key="topic.name">
      <table class="form-catalog__dictionary">
        <thead>
          <tr @click="toggleTopic(topic)">
            <td colspan="2" class="form-catalog__heading">
              <CmkIcon
                class="form-catalog__icon"
                :class="{ 'form-catalog__icon--open': !hiddenTopics[topic.name] }"
                size="xxsmall"
                name="tree-closed"
              />
              {{ topic.title }}
            </td>
          </tr>
        </thead>
        <CmkSpace v-if="!hiddenTopics[topic.name]" size="small" direction="vertical" />
        <tbody v-show="!hiddenTopics[topic.name]">
          <template v-if="isGroupedTopic(topic)">
            <TopicGrouped
              v-model:data="data[topic.name]!"
              :elements="topic.elements as unknown as TopicGroup[]"
              :backend-validation="elementValidation[topic.name]!"
            />
          </template>
          <template v-else>
            <TopicUngrouped
              v-model:data="data[topic.name]!"
              :elements="topic.elements as unknown as TopicElement[]"
              :backend-validation="elementValidation[topic.name]!"
            />
          </template>
        </tbody>
        <CmkSpace v-if="!hiddenTopics[topic.name]" size="small" direction="vertical" />
      </table>
    </template>
  </span>
</template>

<style scoped>
.form-catalog__dictionary {
  width: 100%;
  padding: 0;
  margin: 10px 0;
  background: #f5f5fb;
  border-radius: 4px;
  border-collapse: collapse;
}

.form-catalog__heading {
  position: relative;
  height: auto;
  padding: 4px 10px 3px 9px;
  font-weight: 700;
  letter-spacing: 1px;
  background-color: #e8e8ee;
  vertical-align: middle;
  cursor: pointer;
  border-radius: 4px 4px 0 0;
  white-space: nowrap;
  empty-cells: show;
}

.form-catalog__icon {
  margin-right: 10px;
  transition: transform 0.2s ease-in-out;
  transform: rotate(90deg);
}

.form-catalog__icon--open {
  transform: rotate(0deg);
}
</style>
