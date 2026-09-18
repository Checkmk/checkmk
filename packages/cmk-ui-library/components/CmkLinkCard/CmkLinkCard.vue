<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { type VariantProps, cva } from 'class-variance-authority'
import type { SimpleIcons } from 'cmk-ui-library/components/CmkIcon'
import CmkIcon from 'cmk-ui-library/components/CmkIcon'
import CmkHeading from 'cmk-ui-library/components/typography/CmkHeading.vue'
import CmkParagraph from 'cmk-ui-library/components/typography/CmkParagraph.vue'
import type { TranslatedString } from 'cmk-ui-library/lib/i18nString'
import { computed } from 'vue'

const cmkLinkCardVariants = cva('', {
  variants: {
    borders: {
      standard: 'cmk-link-card--standard',
      borderless: 'cmk-link-card--borderless'
    },
    contrast: {
      standard: 'cmk-link-card--standard-contrast',
      high: 'cmk-link-card--high-contrast'
    }
  },
  defaultVariants: {
    borders: 'standard',
    contrast: 'standard'
  }
})

export type CmkLinkCardBorders = VariantProps<typeof cmkLinkCardVariants>['borders']
export type CmkLinkCardContrast = VariantProps<typeof cmkLinkCardVariants>['contrast']
interface CmkLinkCardProps {
  iconName?: SimpleIcons | undefined
  title: TranslatedString
  subtitle?: TranslatedString
  url?: string | undefined
  callback?: () => void
  openInNewTab: boolean
  disabled?: boolean
  borders?: CmkLinkCardBorders
  contrast?: CmkLinkCardContrast
}
const props = defineProps<CmkLinkCardProps>()

/** A card with nowhere to go is a plain container: no hover, no focus ring, not tabbable. */
const isLink = computed(() => props.url !== undefined || props.callback !== undefined)

const classes = computed(() => [
  cmkLinkCardVariants({ borders: props.borders, contrast: props.contrast }),
  { disabled: props.disabled }
])
</script>

<template>
  <component
    :is="isLink ? 'a' : 'div'"
    :href="isLink ? url || '#' : undefined"
    :target="isLink && openInNewTab ? '_blank' : undefined"
    class="cmk-link-card"
    :class="classes"
    @click="
      (event: Event) => {
        if (!url) {
          event.preventDefault()
        }
        if (props.callback) {
          props.callback()
        }
      }
    "
  >
    <slot name="leading">
      <CmkIcon v-if="iconName" :name="iconName" size="xxlarge" class="cmk-link-card__icon" />
    </slot>
    <div class="cmk-link-card__text-area">
      <CmkHeading type="h4" class="cmk-link-card__heading">{{ title }}</CmkHeading>
      <CmkParagraph v-if="subtitle" class="cmk-link-card__subtitle">{{ subtitle }}</CmkParagraph>
      <div v-if="$slots.default" class="cmk-link-card__content">
        <slot />
      </div>
    </div>
    <CmkIcon v-if="openInNewTab" name="export-link" class="cmk-link-card__export-icon" />
  </component>
</template>

<style scoped>
.cmk-link-card--standard {
  border: var(--dimension-1) solid var(--ux-theme-6);

  --background-color: var(--ux-theme-1);

  &.cmk-link-card--high-contrast {
    --background-color: var(--ux-theme-3);

    border: var(--dimension-1) solid var(--ux-theme-8);
  }
}

.cmk-link-card--borderless {
  border: var(--dimension-1) solid transparent;

  --background-color: var(--ux-theme-2);

  &.cmk-link-card--high-contrast {
    --background-color: var(--ux-theme-3);
  }
}

.cmk-link-card {
  display: flex;
  align-items: center;
  text-decoration: none;
  border-radius: 4px;
  background-color: var(--background-color);
  padding: var(--dimension-4) var(--dimension-5);

  /* stylelint-disable-next-line checkmk/vue-bem-naming-convention */
  &.disabled {
    opacity: 0.5;
    pointer-events: none;
    cursor: default;
  }
}

a.cmk-link-card:hover {
  background-color: color-mix(in srgb, var(--background-color), var(--background-hover-color) 10%);
}

a.cmk-link-card:focus {
  outline: var(--default-border-color-green) auto 1px;
}

a.cmk-link-card:focus-visible {
  outline: revert;
}

body[data-theme='facelift'] {
  .cmk-link-card {
    --background-hover-color: var(--black);
  }
}

body[data-theme='modern-dark'] {
  .cmk-link-card {
    --background-hover-color: var(--white);
  }
}

.cmk-link-card__icon {
  margin-right: var(--dimension-7);
}

/* A title long enough to have no break in it wraps rather than growing the card. */
.cmk-link-card__text-area {
  min-width: 0;
  overflow-wrap: anywhere;
}

.cmk-link-card__content {
  margin-top: var(--dimension-4);
}

.cmk-link-card__subtitle {
  color: var(--font-color-dimmed);
}

.cmk-link-card__export-icon {
  margin-left: auto;
}
</style>
