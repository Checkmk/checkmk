<!--
Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import type {
  Dictionary,
  DictionaryElement,
  TopicGroup
} from 'cmk-shared-typing/typescript/vue_formspec_components'
import { ref } from 'vue'

import useId from '@/lib/useId'
import { immediateWatch } from '@/lib/watch'

import CmkLabel from '@/components/CmkLabel.vue'

import { useFormEditDispatcher } from '@/form/private/FormEditDispatcher/useFormEditDispatcher'
import { type ValidationMessages } from '@/form/private/validation'

const props = defineProps<{
  elements: TopicGroup[]
  backendValidation: ValidationMessages
}>()

const data = defineModel<Record<string, unknown>>('data', { required: true })
const componentId = useId()
const topicGroupValidation = ref<Record<string, ValidationMessages>>({})

function updateTopicGroupValidation(
  elements: TopicGroup[],
  backendValidation: ValidationMessages
): Record<string, ValidationMessages> {
  const updatedValidation: Record<string, ValidationMessages> = {}
  for (const group of elements) {
    updatedValidation[group.title] = backendValidation.filter((msg) =>
      group.elements.some((element) => element.name === msg.location[0])
    )
  }
  return updatedValidation
}

immediateWatch(
  () => [props.elements, props.backendValidation],
  () => {
    topicGroupValidation.value = updateTopicGroupValidation(props.elements, props.backendValidation)
  }
)

function convertToDictionarySpec(topicGroup: TopicGroup): Dictionary {
  return {
    type: 'dictionary',
    title: topicGroup.title,
    help: '',
    additional_static_elements: [],
    validators: [],
    groups: [],
    no_elements_text: '',
    elements: topicGroup.elements.map((element): DictionaryElement => {
      return {
        name: element.name,
        parameter_form: element.parameter_form,
        default_value: element.default_value,
        render_only: false,
        required: element.required,
        group: null
      }
    })
  }
}
// eslint-disable-next-line @typescript-eslint/naming-convention
const { FormEditDispatcher } = useFormEditDispatcher()
</script>

<template>
  <tr
    v-for="topic_group in props.elements"
    :key="`${componentId}.${topic_group.title}`"
    class="form-topic-grouped"
  >
    <td class="form-topic-grouped__group-title">
      <span class="form-topic-grouped__fixed-content-width">
        <CmkLabel v-if="topic_group.title.length > 0" dots>
          {{ topic_group.title }}
        </CmkLabel>
      </span>
    </td>
    <td class="form-topic-grouped__value">
      <FormEditDispatcher
        :spec="convertToDictionarySpec(topic_group)"
        :data="data"
        :backend-validation="topicGroupValidation[topic_group.title]"
      />
    </td>
  </tr>
</template>

<style scoped>
.form-topic-grouped {
  padding-bottom: 4px;
}

.form-topic-grouped__group-title {
  width: 240px;
  min-width: 240px;
  max-width: 240px;
  vertical-align: top;
}

.form-topic-grouped__fixed-content-width {
  width: 230px;
  display: inline-block;
  white-space: nowrap;
  overflow: hidden;
}

.form-topic-grouped__value {
  width: 100%;
  vertical-align: top;
  padding-bottom: 4px;
  empty-cells: show;
  white-space: nowrap;
}

.form-topic-grouped:nth-child(1) > td {
  padding-top: 5px;
}
</style>
