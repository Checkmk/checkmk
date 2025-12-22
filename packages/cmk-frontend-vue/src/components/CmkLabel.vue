<!--
Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { type VariantProps, cva } from 'class-variance-authority'
import { Label } from 'radix-vue'
import { computed, useAttrs } from 'vue'

import type { TranslatedString } from '@/lib/i18nString'

import CmkHelpText from '@/components/CmkHelpText.vue'

defineOptions({
  inheritAttrs: false
})

const labelVariants = cva('', {
  variants: {
    variant: {
      default: '',
      title: 'cmk-label--title',
      subtitle: 'cmk-label--subtitle'
    },
    cursor: {
      default: '',
      pointer: 'cmk-label--cursor-pointer'
    }
  },
  defaultVariants: {
    variant: 'default',
    cursor: 'default'
  }
})
type LabelVariants = VariantProps<typeof labelVariants>

export interface LabelProps {
  for?: string
  variant?: LabelVariants['variant']
  dots?: boolean | undefined
  help?: TranslatedString | undefined
  cursor?: LabelVariants['cursor']
}

const props = defineProps<LabelProps>()
const attrs = useAttrs()

const delegatedProps = computed(() => {
  const { variant: _1, help: _2, cursor: _3, ...delegated } = attrs

  if (props.for) {
    delegated.for = props.for
  }

  return delegated
})
</script>

<template>
  <div class="cmk-label__container">
    <span class="cmk-label__content">
      <Label v-bind="delegatedProps" :class="labelVariants({ variant, cursor })"><slot /></Label
      ><span v-if="help" class="cmk-label--nowrap">&nbsp;<CmkHelpText :help="help" /></span>
    </span>
    <div v-if="dots" class="cmk-label--dots" />
  </div>
</template>

<style scoped>
.cmk-label__container {
  display: inline-flex;
  min-width: 0;
  max-width: 100%;
}

.cmk-label__content {
  flex: 0 1 auto;
  min-width: 0;
}

label {
  &.cmk-label--title {
    height: 24px;
    align-content: center;
    font-weight: var(--font-weight-bold);
    font-size: var(--font-size-xlarge);
  }

  &.cmk-label--subtitle {
    font-size: var(--font-size-normal);
    margin-bottom: var(--spacing);
  }

  &.cmk-label--cursor-pointer {
    cursor: pointer;
  }
}

.cmk-label--nowrap {
  white-space: nowrap;
}

.cmk-label--dots {
  flex: 1 0 0;
  margin-left: 5px;
  color: var(--font-color-dimmed);
  overflow: hidden;
  min-width: 15px;
}

.cmk-label--dots::after {
  content: '........................................................................................................................................................................................................';
}
</style>
