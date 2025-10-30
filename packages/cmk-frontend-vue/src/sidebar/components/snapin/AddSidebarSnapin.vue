<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->

<script setup lang="ts">
import usei18n from '@/lib/i18n'
import type { TSidebarSnapin } from '@/lib/sidebar/type-defs'

import SidebarSnapin from './SidebarSnapin.vue'

const { _t } = usei18n()
const props = defineProps<TSidebarSnapin>()
const emit = defineEmits<{
  'add-snapin': [TSidebarSnapin]
}>()
</script>

<template>
  <div class="sidebar-add-sidebar-snapin__container">
    <SidebarSnapin class="sidebar-add-sidebar-snapin__preview" v-bind="props" />
    <!-- eslint-disable vue/no-v-html-->
    <div
      v-if="props.description"
      class="sidebar-add-sidebar-snapin__description"
      v-html="props.description"
    ></div>
    <button class="sidebar-add-sidebar-snapin__button" @click="emit('add-snapin', props)">
      <span>{{ _t(`Add "${props.title}" to sidebar`) }}</span>
    </button>
  </div>
</template>

<style scoped>
.sidebar-add-sidebar-snapin__container {
  float: left;
  width: 292px;
  position: relative;
  background: var(--default-nav-bg-color);
  border-radius: var(--border-radius);

  .sidebar-add-sidebar-snapin__button {
    display: flex;
    width: 100%;
    height: 100%;
    border: 0;
    margin: 0;
    background: transparent;
    align-items: center;
    justify-content: center;
    position: absolute;
    top: 0;

    span {
      color: transparent;
      background: transparent;
      padding: var(--dimension-5);
      border-radius: var(--border-radius);
    }

    &:hover {
      background: rgb(255 255 255 / 20%);
      border: 1px solid var(--success);

      span {
        color: var(--font-color);
        background: rgb(0 0 0 / 80%);
      }
    }
  }

  .sidebar-add-sidebar-snapin__preview {
    z-index: 0;
    max-height: 200px;
    overflow: hidden;
  }

  .sidebar-add-sidebar-snapin__description {
    flex-grow: 1;
    border-top: 1px solid var(--default-border-color);
    padding-top: var(--dimension-5);
    margin: var(--dimension-5);
  }
}
</style>
