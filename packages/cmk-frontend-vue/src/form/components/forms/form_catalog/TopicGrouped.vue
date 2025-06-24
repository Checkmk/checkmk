<!--
Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import type {
  Dictionary,
  DictionaryElement,
  I18NFormSpecBase,
  TopicGroup
} from 'cmk-shared-typing/typescript/vue_formspec_components'
import { type ValidationMessages } from '@/form/components/utils/validation'
import { useId } from '@/form/utils'
import { useFormEditDispatcher } from '@/form/private'

const props = defineProps<{
  elements: TopicGroup[]
  backendValidation: ValidationMessages
  i18nBase: I18NFormSpecBase
}>()

const data = defineModel<Record<string, unknown>>('data', { required: true })
const componentId = useId()

function convertToDictionarySpec(topicGroup: TopicGroup): Dictionary {
  return {
    type: 'dictionary',
    title: topicGroup.title,
    help: '',
    additional_static_elements: [],
    validators: [],
    groups: [],
    no_elements_text: '',
    i18n_base: props.i18nBase,
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
  <tr v-for="topic_group in props.elements" :key="`${componentId}.${topic_group.title}`">
    <td class="group_title">
      <span class="fixed_content_width">
        <label>
          {{ topic_group.title }}
        </label>
        <span class="dots">{{ Array(200).join('.') }}</span>
      </span>
    </td>
    <td class="value">
      <FormEditDispatcher
        :spec="convertToDictionarySpec(topic_group)"
        :data="data"
        :backend-validation="[]"
      />
    </td>
  </tr>
</template>

<style scoped>
tr {
  padding-bottom: 4px;
}

td.group_title {
  width: 240px;
  min-width: 240px;
  max-width: 240px;
  vertical-align: top;
  span.fixed_content_width {
    width: 230px;
    display: inline-block;
    white-space: nowrap;
    overflow: hidden;
  }
}

td.value {
  width: 100%;
  vertical-align: top;
  padding-bottom: 4px;
}
</style>
