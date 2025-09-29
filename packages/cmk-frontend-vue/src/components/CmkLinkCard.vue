<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { type VariantProps, cva } from 'class-variance-authority'
import { computed } from 'vue'

import type { TranslatedString } from '@/lib/i18nString'

import CmkIcon from '@/components/CmkIcon.vue'
import CmkHeading from '@/components/typography/CmkHeading.vue'
import CmkParagraph from '@/components/typography/CmkParagraph.vue'

const cmkLinkCardVariants = cva('', {
  variants: {
    variant: {
      standard: 'cmk-link-card--standard',
      borderless: 'cmk-link-card--borderless'
    }
  },
  defaultVariants: {
    variant: 'standard'
  }
})

export type CmkLinkCardVariants = VariantProps<typeof cmkLinkCardVariants>
interface CmkLinkCardProps {
  iconName?: string | undefined
  title: TranslatedString
  subtitle?: TranslatedString
  url?: string
  callback?: () => void
  openInNewTab: boolean
  disabled?: boolean
  variant?: CmkLinkCardVariants['variant']
}
const props = defineProps<CmkLinkCardProps>()
const classes = computed(() => [
  cmkLinkCardVariants({ variant: props.variant }),
  { disabled: props.disabled }
])
</script>

<template>
  <a
    :href="url || 'javascript:void(0)'"
    :target="openInNewTab ? '_blank' : ''"
    class="cmk-link-card"
    :class="classes"
    @click="
      () => {
        if (props.callback) {
          props.callback()
        }
      }
    "
  >
    <CmkIcon v-if="iconName" :name="iconName" size="xxlarge" class="cmk-link-card__icon" />
    <div class="cmk-link-card__text-area">
      <CmkHeading type="h4" class="cmk-link-card__heading">{{ title }}</CmkHeading>
      <CmkParagraph v-if="subtitle" class="cmk-link-card__subtitle">{{ subtitle }}</CmkParagraph>
    </div>
    <CmkIcon v-if="openInNewTab" name="export-link" class="cmk-link-card__export-icon" />
  </a>
</template>

<style scoped>
.cmk-link-card--standard {
  background-color: var(--ux-theme-1);
  border: var(--dimension-1) solid var(--ux-theme-6);
}

.cmk-link-card--borderless {
  background-color: var(--ux-theme-2);
}

.cmk-link-card {
  display: flex;
  align-items: center;
  text-decoration: none;
  border-radius: 4px;
  padding: var(--dimension-4) var(--dimension-5);

  &:hover {
    background-color: var(--ux-theme-5);
  }

  &:focus,
  &:focus-visible {
    outline: var(--default-border-color-green) auto 1px;
  }

  /* stylelint-disable-next-line checkmk/vue-bem-naming-convention */
  &.disabled {
    opacity: 0.5;
    pointer-events: none;
    cursor: default;
  }
}

.cmk-link-card__icon {
  margin-right: var(--dimension-7);
}

.cmk-link-card__subtitle {
  color: var(--font-color-dimmed);
}

.cmk-link-card__export-icon {
  margin-left: auto;
}
</style>
