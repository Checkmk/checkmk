<!--
Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { ref } from 'vue'
import FormEdit from '@/form/components/FormEdit.vue'

import type { Tuple, String, SingleChoice } from '@/form/components/vue_formspec_components'

defineProps<{ screenshotMode: boolean }>()

const data = ref<Array<string>>(['eins', 'zwei'])

function getStringSpec(name: string): String {
  return {
    type: 'string',
    title: `title ${name}`,
    help: `some string help ${name}`,
    input_hint: `some string input hint ${name}`,
    field_size: 'SMALL',
    autocompleter: null,
    validators: []
  }
}

function getSingleChoiceSpec(name: string): SingleChoice {
  return {
    type: 'single_choice',
    title: '',
    help: '',
    validators: [],
    no_elements_text: '',
    frozen: false,
    label: name,
    input_hint: 'Please choose',
    elements: [
      {
        name: '1',
        title: 'Any'
      },
      {
        name: '2',
        title: 'UP'
      },
      {
        name: '3',
        title: 'DOWN'
      },
      {
        name: '4',
        title: 'UNREACHABLE'
      }
    ]
  }
}

function getTupleSpec(
  layout: Tuple['layout'],
  showTitles: Tuple['show_titles'],
  embeddedFormSpec: string
): Tuple {
  const embedded = embeddedFormSpec === 'string' ? getStringSpec : getSingleChoiceSpec
  return {
    type: 'tuple',
    title: 'some title',
    help: 'some help',
    validators: [],
    layout: layout,
    show_titles: showTitles,
    elements: [embedded('string1'), embedded('string2')]
  }
}

const layouts: Array<Tuple['layout']> = ['horizontal_titles_top', 'horizontal', 'vertical', 'float']
</script>

<template>
  <div v-for="embeddedFormSpec in ['string', 'singleChoice']" :key="embeddedFormSpec">
    {{ embeddedFormSpec }}
    <table>
      <thead>
        <tr>
          <td>layout</td>
          <td>show_titles=true</td>
          <td>show_titles=false</td>
        </tr>
      </thead>
      <tbody>
        <tr v-for="layout in layouts" :key="layout">
          <td>{{ layout }}</td>
          <td v-for="showTitles in [true, false]" :key="JSON.stringify(showTitles)">
            <FormEdit
              :spec="getTupleSpec(layout, showTitles, embeddedFormSpec)"
              :backend-validation="[]"
              :data="data"
            />
          </td>
        </tr>
      </tbody>
    </table>
  </div>

  <hr />
  <h2>readonly tuple with backend validation result</h2>
  THIS IS CURRENTLY BROKEN; BACKEND VALIDATION WILL NOT BE RENDERED
  <FormReadonly
    :spec="getTupleSpec('horizontal', true, 'string')"
    :data="['one', 'two']"
    :backend-validation="[{ location: ['1'], message: 'error', invalid_value: 'smth' }]"
  />
</template>

<style scoped>
table {
  border-collapse: collapse;
}
table td {
  padding: 5px;
  border: 1px solid black;
}
</style>
