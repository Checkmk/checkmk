<!--
Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts" generic="T extends 'text' | 'number' = 'text'">
import { ref, watch } from 'vue'
import { immediateWatch } from '@/lib/watch'
import { cva, type VariantProps } from 'class-variance-authority'
import CmkSpace from '@/components/CmkSpace.vue'
import CmkInlineValidation from '@/components/user-input/CmkInlineValidation.vue'
import { inputSizes } from './sizes'

defineOptions({ inheritAttrs: false })

const propsCva = cva('cmk-input', {
  variants: {
    type: {
      text: 'cmk-input--text',
      number: 'cmk-input--number'
    }
  }
})

type InputType = NonNullable<VariantProps<typeof propsCva>['type']>
type InputDataType<TType extends InputType> = TType extends 'number' ? number : string

const {
  type = 'text',
  fieldSize = 'SMALL',
  unit,
  externalErrors,
  validators
} = defineProps<{
  type?: T
  fieldSize?: keyof typeof inputSizes
  unit?: string
  externalErrors?: string[]
  validators?: ((value: InputDataType<T>) => string[])[]
}>()

const data = defineModel<InputDataType<T>>()
const validation = ref<string[]>([])

watch(data, (newData) => {
  if (newData !== undefined && validators && validators.length > 0) {
    validation.value =
      validators.reduce((acc, validator) => {
        return [...acc, ...validator(newData)]
      }, [] as string[]) || []
  }
})

immediateWatch(
  () => externalErrors,
  (newErrors) => {
    if (newErrors === undefined) {
      validation.value = []
      return
    }
    validation.value = newErrors
  }
)
</script>

<template>
  <input
    v-model="data"
    v-bind="$attrs"
    :class="propsCva({ type })"
    :type="type"
    :size="inputSizes[fieldSize].width"
    step="any"
  />
  <span v-if="unit"><CmkSpace size="small" />{{ unit }}</span>
  <CmkInlineValidation :validation="validation"></CmkInlineValidation>
</template>

<style scoped>
input.cmk-input--number::-webkit-outer-spin-button,
input.cmk-input--number::-webkit-inner-spin-button {
  -webkit-appearance: none;
  margin: 0;
}

input.cmk-input--number {
  width: 5.8ex;
  -moz-appearance: textfield;
}
</style>
