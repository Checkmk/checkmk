<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import CmkIcon from '@/components/CmkIcon.vue'
import CmkParagraph from '@/components/typography/CmkParagraph.vue'
import CmkHeading from '@/components/typography/CmkHeading.vue'
import { cva, type VariantProps } from 'class-variance-authority'
import { computed } from 'vue'

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
  iconName?: string
  title: string
  subtitle?: string
  url: string
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
  <a :href="url" :target="openInNewTab ? '_blank' : ''" class="cmk-link-card" :class="classes">
    <CmkIcon v-if="iconName" :name="iconName" size="xxlarge" class="cmk-link-card__icon" />
    <div class="cmk-link-card__text-area">
      <CmkHeading type="h4" class="cmk-link-card__heading">{{ title }}</CmkHeading>
      <CmkParagraph :v-if="subtitle" class="cmk-link-card__subtitle">{{ subtitle }}</CmkParagraph>
    </div>
    <CmkIcon v-if="openInNewTab" name="export_link" class="cmk-link-card__export-icon" />
  </a>
</template>

<style scoped>
.cmk-link-card--standard {
  background-color: var(--ux-theme-1);
  border: 1px solid var(--default-border-color);
}
.cmk-link-card--borderless {
  background-color: var(--ux-theme-2);
}
.cmk-link-card {
  display: flex;
  align-items: center;
  text-decoration: none;
  border-radius: 4px;
  padding: var(--spacing);
  margin-bottom: var(--spacing);

  &:hover {
    background-color: var(--ux-theme-5);
  }
  &:focus,
  &:focus-visible {
    outline: var(--default-border-color-green) auto 1px;
  }
  &.disabled {
    opacity: 50%;
    pointer-events: none;
    cursor: default;
  }
}
.cmk-link-card__icon {
  margin-right: var(--spacing);
}
.cmk-link-card__text-area {
  margin-right: var(--spacing);
}
.cmk-link-card__subtitle {
  color: var(--font-color-dimmed);
}
.cmk-link-card__export-icon {
  margin-left: auto;
}
</style>
