<!--
Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import CmkButton from '@/components/CmkButton.vue'
import CmkIcon from '@/components/CmkIcon.vue'
import CmkSpace from '@/components/CmkSpace.vue'

const { buttonPadding = '16px', ...props } = defineProps<{
  removeElement: () => void
  style?: 'first' | 'last' | 'only' | null
  buttonPadding?: '16px' | '8px'
  draggable?: {
    dragStart: (event: DragEvent) => void
    dragEnd: (event: DragEvent) => void
    dragging: (event: DragEvent) => void | null
  } | null
}>()
</script>

<template>
  <div class="cmk_list__element">
    <div
      :class="{
        cmk_list__button_container: true,
        only: props.style === 'only',
        first: props.style === 'first',
        last: props.style === 'last'
      }"
    >
      <div class="cmk_list__buttons">
        <template v-if="draggable!!">
          <CmkButton
            variant="transparent"
            aria-label="Drag to reorder"
            :draggable="true"
            @dragstart="draggable?.dragStart"
            @drag="draggable?.dragging"
            @dragend="draggable?.dragEnd"
            @click.prevent="() => {}"
          >
            <CmkIcon name="drag" size="small" style="pointer-events: none" />
          </CmkButton>
          <CmkSpace direction="horizontal" />
        </template>
        <CmkButton variant="transparent" @click.prevent="() => removeElement()">
          <CmkIcon name="close" size="small" />
        </CmkButton>
      </div>
    </div>
    <div
      :class="{
        cmk_list__content: true,
        only: props.style === 'only',
        first: props.style === 'first',
        last: props.style === 'last'
      }"
    >
      <slot></slot>
    </div>
  </div>
</template>

<style scoped>
.cmk_list__element {
  --button-padding-top: 4px;

  .cmk_list__button_container,
  .cmk_list__content {
    display: inline-block;
    vertical-align: top;
    padding: var(--spacing) 0;

    .cmk_list__buttons {
      display: flex;
    }
  }

  .cmk_list__content {
    padding-top: calc(var(--spacing) - var(--button-padding-top));
    padding-left: v-bind(buttonPadding);
  }

  .cmk_list__content.only {
    padding-top: 0;
    padding-bottom: 0;
  }

  .cmk_list__button_container.only {
    padding-top: var(--button-padding-top);
    padding-bottom: var(--button-padding-top);
  }

  .cmk_list__button_container.first {
    padding-top: var(--button-padding-top);
  }

  .cmk_list__content.first {
    padding-top: 0;
  }

  .cmk_list__button_container.last,
  .cmk_list__content.last {
    padding-bottom: 0;
  }
}
</style>
