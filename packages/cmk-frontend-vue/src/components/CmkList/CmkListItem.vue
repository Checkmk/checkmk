<!--
Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { type VariantProps, cva } from 'class-variance-authority'
import CmkIconButton from '@/components/CmkIconButton.vue'
import CmkSpace from '@/components/CmkSpace.vue'

const listItemVariants = cva('', {
  variants: {
    variant: {
      default: '',
      first: 'cmk-list-item--first',
      last: 'cmk-list-item--last',
      only: 'cmk-list-item--only'
    }
  },
  defaultVariants: {
    variant: 'default'
  }
})
type ListItemVariants = VariantProps<typeof listItemVariants>

const { buttonPadding = '16px' } = defineProps<{
  removeElement: () => void
  variant?: ListItemVariants['variant']
  buttonPadding?: '16px' | '8px'
  draggable?: {
    dragStart: (event: DragEvent) => void
    dragEnd: (event: DragEvent) => void
    dragging: (event: DragEvent) => void | null
  } | null
}>()
</script>

<template>
  <div class="cmk-list-item" :class="listItemVariants({ variant })">
    <div class="cmk-list-item__button-container">
      <div class="cmk-list-item__buttons">
        <template v-if="draggable!!">
          <CmkIconButton
            name="drag"
            size="small"
            style="pointer-events: none"
            aria-label="Drag to reorder"
            :draggable="true"
            @dragstart="draggable?.dragStart"
            @drag="draggable?.dragging"
            @dragend="draggable?.dragEnd"
            @click.prevent="() => {}"
          />
          <CmkSpace direction="horizontal" />
        </template>
        <CmkIconButton
          name="close"
          size="small"
          aria-label="Remove element"
          @click.prevent="() => removeElement()"
        />
      </div>
    </div>
    <div class="cmk-list-item__content">
      <slot></slot>
    </div>
  </div>
</template>

<style scoped>
.cmk-list-item {
  --button-padding-top: 4px;

  .cmk-list-item__button-container,
  .cmk-list-item__content {
    display: inline-block;
    vertical-align: top;
    padding: var(--spacing) 0;

    .cmk-list-item__buttons {
      display: flex;
    }
  }

  .cmk-list-item__content {
    padding-top: calc(var(--spacing) - var(--button-padding-top));
    padding-left: v-bind(buttonPadding);
  }

  &.cmk-list-item--first {
    > .cmk-list-item__button-container {
      padding-top: var(--button-padding-top);
    }

    > .cmk-list-item__content {
      padding-top: 0;
    }
  }

  &.cmk-list-item--last {
    > .cmk-list-item__button-container,
    > .cmk-list-item__content {
      padding-bottom: 0;
    }
  }

  &.cmk-list-item--only {
    > .cmk-list-item__button-container {
      padding-top: var(--button-padding-top);
      padding-bottom: var(--button-padding-top);
    }

    > .cmk-list-item__content {
      padding-top: 0;
      padding-bottom: 0;
    }
  }
}
</style>
