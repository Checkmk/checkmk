<!--
Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import type {
  Catalog,
  Dictionary,
  Topic,
  TopicElement,
  TopicGroup
} from 'cmk-shared-typing/typescript/vue_formspec_components'
import { ref } from 'vue'

import { untranslated } from '@/lib/i18n'
import { immediateWatch } from '@/lib/watch'

import CmkAlertBox from '@/components/CmkAlertBox.vue'
import CmkCatalogPanel from '@/components/CmkCatalogPanel.vue'
import FormValidation from '@/components/user-input/CmkInlineValidation.vue'

import FormReadonly from '@/form/FormReadonly.vue'
import TopicGrouped from '@/form/private/forms/FormCatalog/TopicGrouped.vue'
import TopicUngrouped from '@/form/private/forms/FormCatalog/TopicUngrouped.vue'
import { type ValidationMessages, groupNestedValidations } from '@/form/private/validation'

const props = defineProps<{
  spec: Catalog
  backendValidation: ValidationMessages
}>()

const data = defineModel<Record<string, Record<string, unknown>>>('data', { required: true })

const elementValidation = ref<Record<string, ValidationMessages>>({})
const validation = ref<ValidationMessages>([])
immediateWatch(
  () => props.backendValidation,
  (newValidation: ValidationMessages) => {
    const [catalogValidation, nestedValidation] = groupNestedValidations(
      props.spec.elements,
      newValidation
    )
    elementValidation.value = nestedValidation
    validation.value = catalogValidation
  }
)

function isGroupedTopic(topic: Topic): boolean {
  if (topic.elements.length === 0) {
    return false
  }
  return topic.elements[0]!.type === 'topic_group'
}

interface DictionaryData {
  id: string
  data: Record<string, unknown>
  spec: Dictionary
}

function computeDictionaries(topic: Topic): DictionaryData[] {
  const topicData = data.value[topic.name]
  const dictionaries: DictionaryData[] = []
  for (const element of topic.elements) {
    if (element.type === 'topic_group') {
      for (const subElement of element.elements) {
        const subElementData: Record<string, unknown> = {}
        if (topicData === undefined) {
          subElementData[subElement.name] = {}
        } else {
          subElementData[subElement.name] = topicData[subElement.name]
        }
        dictionaries.push({
          id: `${topic.name}-${subElement.name}`,
          data: subElementData,
          spec: {
            type: 'dictionary',
            title: element.title,
            help: '',
            validators: [],
            elements: [
              {
                name: subElement.name,
                required: true,
                group: null,
                default_value: null,
                render_only: false,
                parameter_form: subElement.parameter_form
              }
            ],
            groups: [],
            no_elements_text: '',
            additional_static_elements: null
          }
        })
      }
    } else if (element.type === 'topic_element') {
      const elementData: Record<string, unknown> = {}
      if (topicData === undefined) {
        elementData[element.name] = {}
      } else {
        elementData[element.name] = topicData[element.name]
      }
      dictionaries.push({
        id: `${topic.name}-${element.name}`,
        data: elementData,
        spec: {
          type: 'dictionary',
          title: topic.title,
          help: '',
          validators: [],
          elements: [
            {
              name: element.name,
              required: true,
              group: null,
              default_value: null,
              render_only: false,
              parameter_form: element.parameter_form
            }
          ],
          groups: [],
          no_elements_text: '',
          additional_static_elements: null
        }
      })
    }
  }
  return dictionaries
}
</script>

<template>
  <div class="form-catalog__container">
    <FormValidation :validation="validation.map((m) => m.message)"></FormValidation>
    <CmkCatalogPanel
      v-for="topic in props.spec.elements"
      :key="topic.name"
      :title="untranslated(topic.title)"
    >
      <div v-if="topic.locked === null">
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
      </div>
      <div v-else>
        <CmkAlertBox variant="warning">
          {{ topic.locked.message }}
        </CmkAlertBox>
        <FormReadonly
          v-for="dictionary in computeDictionaries(topic)"
          :key="dictionary.id"
          v-model:data="dictionary.data"
          :backend-validation="[]"
          :spec="dictionary.spec"
        />
      </div>
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
