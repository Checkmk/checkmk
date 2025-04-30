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
import { groupNestedValidations, type ValidationMessages } from '@/form/components/utils/validation'
import CmkSpace from '@/components/CmkSpace.vue'
import TopicUngrouped from '@/form/components/forms/form_catalog/TopicUngrouped.vue'
import TopicGrouped from '@/form/components/forms/form_catalog/TopicGrouped.vue'

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

function getClass(name: string) {
  return {
    open: !hiddenTopics.value[name],
    closed: hiddenTopics.value[name]
  }
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
      <table class="dictionary nform">
        <thead>
          <tr class="heading" @click="toggleTopic(topic)">
            <td colspan="2">
              <img class="vue nform treeangle" :class="getClass(topic.name)" />
              {{ topic.title }}
            </td>
          </tr>
        </thead>
        <CmkSpace v-if="!hiddenTopics[topic.name]" size="small" direction="vertical" />
        <tbody :class="getClass(topic.name)">
          <template v-if="isGroupedTopic(topic)">
            <TopicGrouped
              v-model:data="data[topic.name]!"
              :elements="topic.elements as unknown as TopicGroup[]"
              :backend-validation="elementValidation[topic.name]!"
              :i18n-base="props.spec.i18n_base"
            />
          </template>
          <template v-else>
            <TopicUngrouped
              v-model:data="data[topic.name]!"
              :elements="topic.elements as unknown as TopicElement[]"
              :backend-validation="elementValidation[topic.name]!"
              :i18n-base="props.spec.i18n_base"
            />
          </template>
        </tbody>
        <CmkSpace v-if="!hiddenTopics[topic.name]" size="small" direction="vertical" />
      </table>
    </template>
  </span>
</template>
