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

import { untranslated } from '@/lib/i18n'
import { immediateWatch } from '@/lib/watch'

import CmkCatalogPanel from '@/components/CmkCatalogPanel.vue'

import TopicGrouped from '@/form/components/forms/form_catalog/TopicGrouped.vue'
import TopicUngrouped from '@/form/components/forms/form_catalog/TopicUngrouped.vue'
import { type ValidationMessages, groupNestedValidations } from '@/form/components/utils/validation'

const props = defineProps<{
  spec: Catalog
  backendValidation: ValidationMessages
}>()

const data = defineModel<Record<string, Record<string, unknown>>>('data', { required: true })

const elementValidation = ref<Record<string, ValidationMessages>>({})
immediateWatch(
  () => props.backendValidation,
  (newValidation: ValidationMessages) => {
    const [, nestedValidation] = groupNestedValidations(props.spec.elements, newValidation)
    elementValidation.value = nestedValidation
  }
)

function isGroupedTopic(topic: Topic): boolean {
  if (topic.elements.length === 0) {
    return false
  }
  return topic.elements[0]!.type === 'topic_group'
}
</script>

<template>
  <div class="form-catalog__container">
    <CmkCatalogPanel
      v-for="topic in props.spec.elements"
      :key="topic.name"
      :title="untranslated(topic.title)"
    >
      <TopicGrouped
        v-if="isGroupedTopic(topic)"
        v-model:data="data[topic.name]!"
        :elements="topic.elements as unknown as TopicGroup[]"
        :backend-validation="elementValidation[topic.name]!"
      />
      <TopicUngrouped
        v-else
        v-model:data="data[topic.name]!"
        :elements="topic.elements as unknown as TopicElement[]"
        :backend-validation="elementValidation[topic.name]!"
      />
    </CmkCatalogPanel>
  </div>
</template>

<style scoped>
.form-catalog__container {
  display: flex;
  flex-direction: column;
  gap: var(--spacing);
}
</style>
