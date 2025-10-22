<!--
Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { cva } from 'class-variance-authority'
import type * as FormSpec from 'cmk-shared-typing/typescript/vue_formspec_components'
import { computed, ref } from 'vue'

import { untranslated } from '@/lib/i18n'
import { immediateWatch } from '@/lib/watch'

import CmkHelpText from '@/components/CmkHelpText.vue'
import CmkHtml from '@/components/CmkHtml.vue'
import FormIndent from '@/components/CmkIndent.vue'
import CmkCheckbox from '@/components/user-input/CmkCheckbox.vue'
import FormValidation from '@/components/user-input/CmkInlineValidation.vue'

import { type ValidationMessages, groupNestedValidations } from '@/form/components/utils/validation'
import { useFormEditDispatcher } from '@/form/private'
import FormHelp from '@/form/private/FormHelp.vue'
import FormRequired from '@/form/private/FormRequired.vue'
import { rendersRequiredLabelItself } from '@/form/private/requiredValidator'
import { useId } from '@/form/utils'

import { getElementsInGroupsFromProps, titleRequired, toggleElement } from './_groups'

const dictionaryVariants = cva('', {
  variants: {
    group_layout: {
      none: '',
      horizontal: 'form-dictionary--horizontal-groups',
      vertical: 'form-dictionary--vertical-groups'
    }
  },
  defaultVariants: {
    group_layout: 'none'
  }
})

const props = defineProps<{
  spec: FormSpec.Dictionary
  backendValidation: ValidationMessages
}>()

const data = defineModel<Record<string, unknown>>('data', { required: true })
const elementValidation = ref<Record<string, ValidationMessages>>({})
const validation = ref<ValidationMessages>([])

immediateWatch(
  () => props.spec.additional_static_elements,
  (newAdditionalStaticElements: FormSpec.Dictionary['additional_static_elements'] | undefined) => {
    if (newAdditionalStaticElements) {
      for (const [key, value] of Object.entries(newAdditionalStaticElements)) {
        data.value[key] = value
      }
    }
  }
)

immediateWatch(
  () => props.backendValidation,
  (newValidation: ValidationMessages) => {
    const [dictionaryValidation, dictionaryElementsValidation] = groupNestedValidations(
      props.spec.elements,
      newValidation
    )
    elementValidation.value = dictionaryElementsValidation
    validation.value = dictionaryValidation
  }
)

function indentRequired(
  element: FormSpec.DictionaryElement,
  layout: FormSpec.DictionaryGroupLayout
): boolean {
  return (
    titleRequired(element) &&
    !(element.group && layout === 'horizontal') &&
    !(
      element.parameter_form.type === 'fixed_value' &&
      !(element.parameter_form as FormSpec.FixedValue).label &&
      !(element.parameter_form as FormSpec.FixedValue).value
    )
  )
}

const groups = computed(() => getElementsInGroupsFromProps(props.spec.elements, data))

const componentId = useId()

// eslint-disable-next-line @typescript-eslint/naming-convention
const { FormEditDispatcher } = useFormEditDispatcher()
</script>

<template>
  <table
    v-if="props.spec.elements.length > 0"
    class="form-dictionary"
    :aria-label="props.spec.title"
    role="group"
  >
    <tbody>
      <tr v-for="group in groups" :key="`${componentId}.${group.groupKey}`">
        <td class="form-dictionary__dictleft">
          <div v-if="!!group.title" class="form-dictionary__group-title">{{ group?.title }}</div>
          <FormHelp v-if="group.help" :help="group.help" />
          <div
            class="form-dictionary__group-elems"
            :class="dictionaryVariants({ group_layout: group.layout })"
          >
            <template
              v-for="dict_element in group.elems"
              :key="`${componentId}.${dict_element.dict_config.name}`"
            >
              <div
                v-if="!dict_element.dict_config.render_only"
                class="form-dictionary__group_elem"
                role="group"
                :aria-label="dict_element.dict_config.parameter_form.title"
              >
                <span
                  v-if="titleRequired(dict_element.dict_config)"
                  class="form-dictionary__group-elem__title"
                >
                  <span
                    v-if="dict_element.dict_config.required"
                    :class="{
                      'form-dictionary__required-without-indent': !indentRequired(
                        dict_element.dict_config,
                        group.layout
                      )
                    }"
                  >
                    <CmkHtml :html="dict_element.dict_config.parameter_form.title" /><FormRequired
                      v-if="!rendersRequiredLabelItself(dict_element.dict_config.parameter_form)"
                      :spec="dict_element.dict_config.parameter_form"
                      :space="'before'"
                    /><template v-if="dict_element.dict_config.parameter_form.help"
                      >&nbsp;<CmkHelpText
                        :help="untranslated(dict_element.dict_config.parameter_form.help)"
                    /></template>
                  </span>
                  <CmkCheckbox
                    v-else
                    v-model="dict_element.is_active"
                    :padding="
                      dict_element.is_active &&
                      indentRequired(dict_element.dict_config, group.layout)
                        ? 'top'
                        : 'both'
                    "
                    :label="untranslated(dict_element.dict_config.parameter_form.title)"
                    :help="untranslated(dict_element.dict_config.parameter_form.help)"
                    @update:model-value="
                      toggleElement(data, spec.elements, dict_element.dict_config.name)
                    "
                  />
                </span>
                <FormIndent
                  v-if="dict_element.is_active"
                  :indent="indentRequired(dict_element.dict_config, group.layout)"
                >
                  <FormEditDispatcher
                    v-model:data="data[dict_element.dict_config.name]"
                    :spec="dict_element.dict_config.parameter_form"
                    :backend-validation="elementValidation[dict_element.dict_config.name]!"
                  />
                </FormIndent>
              </div>
            </template>
          </div>
        </td>
      </tr>
    </tbody>
  </table>
  <span v-else>{{ spec.no_elements_text }}</span>
  <FormValidation :validation="validation.map((m) => m.message)"></FormValidation>
</template>

<style scoped>
.form-dictionary {
  border-collapse: collapse;
  width: 100%;
}

.form-dictionary__group-title {
  font-weight: bold;
  margin: var(--spacing) 0;
}

tr:first-of-type > td > .form-dictionary__group-title {
  margin-top: 0;
}

/* stylelint-disable-next-line checkmk/vue-bem-naming-convention */
.form-dictionary__group_elem {
  margin-bottom: var(--spacing);
}

/* stylelint-disable-next-line checkmk/vue-bem-naming-convention */
tr:last-of-type > td > div > .form-dictionary__group_elem:last-of-type {
  margin-bottom: 0;
}

.form-dictionary__required-without-indent {
  display: inline-block;
  margin-bottom: var(--spacing-half);
}

.form-dictionary__group-elems {
  flex-direction: row;
  gap: 0.5em;
}

.form-dictionary--horizontal-groups {
  display: flex;
}
</style>
