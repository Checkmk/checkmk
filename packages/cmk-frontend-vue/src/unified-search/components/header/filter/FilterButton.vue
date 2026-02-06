<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import CmkBadge, { type Colors, type Types } from '@/components/CmkBadge.vue'
import CmkMultitoneIcon from '@/components/CmkIcon/CmkMultitoneIcon.vue'
import type {
  CmkMultitoneIconColor,
  CmkMultitoneIconNames,
  CustomIconColor
} from '@/components/CmkIcon/types'

const props = defineProps<{
  active?: boolean | undefined
  activeColor: Colors
  icon?:
    | {
        name: CmkMultitoneIconNames
        activeColor: CmkMultitoneIconColor | CustomIconColor
      }
    | undefined
}>()

function getBadgeColor(): Colors {
  return props.active ? props.activeColor : 'default'
}

function getBadgeType(): Types {
  return props.active ? 'fill' : 'outline'
}

function getIconColor(): CmkMultitoneIconColor | CustomIconColor {
  return props.active ? props.icon?.activeColor : 'font'
}
</script>

<template>
  <button
    class="unified-search-filter-button__button"
    :class="{ 'unified-search-filter-button--active': props.active }"
  >
    <CmkBadge
      :color="getBadgeColor()"
      :type="getBadgeType()"
      size="small"
      class="unified-search-filter-button__chip"
    >
      <CmkMultitoneIcon
        v-if="icon"
        :name="icon.name"
        :primary-color="getIconColor()"
        size="small"
        class="unified-search-filter-button__icon"
      />
      <slot />
    </CmkBadge>
  </button>
</template>

<style scoped>
.unified-search-filter-button__button {
  padding: 0;
  margin: 0;
  border: 1px solid transparent;
  border-radius: var(--border-radius);
  background: transparent;
  font-weight: var(--font-weight-default);

  &:focus-visible {
    border-color: var(--success);
  }

  .unified-search-filter-button__chip {
    border-width: 1px;
    padding: var(--dimension-3) var(--dimension-4);
    margin: 0;
    font-size: var(--font-size-default);

    /* stylelint-disable-next-line checkmk/vue-bem-naming-convention */
    &.cmk-badge--default {
      border-color: var(--ux-theme-6);
    }

    .unified-search-filter-button__icon {
      margin-right: var(--dimension-3);
    }
  }

  &:not(.unified-search-filter-button--active) {
    &:hover {
      .unified-search-filter-button__chip {
        background-color: var(--ux-theme-4);
      }
    }
  }
}
</style>
