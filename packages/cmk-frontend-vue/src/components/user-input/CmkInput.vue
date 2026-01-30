<!--
Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script
  setup
  lang="ts"
  generic="T extends 'text' | 'number' | 'date' | 'time' | 'password' = 'text'"
>
import { type VariantProps, cva } from 'class-variance-authority'
import { computed, ref, watch } from 'vue'

import { immediateWatch } from '@/lib/watch'

import CmkSpace from '@/components/CmkSpace.vue'
import CmkInlineValidation from '@/components/user-input/CmkInlineValidation.vue'

import { inputSizes } from './sizes'

defineOptions({ inheritAttrs: false })

const propsCva = cva('cmk-input', {
  variants: {
    type: {
      text: 'cmk-input--text',
      number: 'cmk-input--number',
      date: 'cmk-input--date',
      time: 'cmk-input--time',
      password: 'cmk-input--password'
    }
  }
})

type InputType = NonNullable<VariantProps<typeof propsCva>['type']>
type InputDataType<TType extends InputType> = TType extends 'number' ? number | undefined : string

const {
  type = 'text',
  fieldSize = 'SMALL',
  unit,
  externalErrors,
  validators,
  inline = false
} = defineProps<{
  type?: T
  fieldSize?: keyof typeof inputSizes
  unit?: string
  externalErrors?: string[]
  validators?: ((value: InputDataType<T>) => string[])[]
  inline?: boolean
}>()

const wrapperStyle = computed(() => (inline ? { display: 'inline-block' } : undefined))

const data = defineModel<InputDataType<T>>()
const validation = ref<string[]>([])
const width = computed(() => inputSizes[fieldSize].width)

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
  <div class="cmk-input__wrapper" :style="wrapperStyle">
    <CmkInlineValidation :validation="validation"></CmkInlineValidation>
    <div class="cmk-input__input-unit-container">
      <input
        v-model="data"
        v-bind="$attrs"
        :class="[propsCva({ type }), { 'cmk-input--error': validation.length > 0 }]"
        :type="type"
        step="any"
      />
      <div v-if="unit" class="cmk-input__unit"><CmkSpace size="small" />{{ unit }}</div>
    </div>
  </div>
</template>

<style scoped>
.cmk-input__wrapper {
  display: flex;
  flex-direction: column;
}

.cmk-input__input-unit-container {
  display: flex;
  align-items: flex-end;
}

.cmk-input__unit {
  padding-bottom: 3px;
}

.cmk-input--error {
  border: 1px solid var(--inline-error-border-color);
}

input.cmk-input--number::-webkit-outer-spin-button,
input.cmk-input--number::-webkit-inner-spin-button {
  appearance: none;
  margin: 0;
}

input.cmk-input--number {
  width: 5.8ex;
  appearance: textfield;
  text-align: right;
}

input.cmk-input--text {
  width: v-bind('width');
}
</style>
