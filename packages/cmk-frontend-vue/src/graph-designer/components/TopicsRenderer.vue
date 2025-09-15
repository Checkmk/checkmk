<!--
Copyright (C) 2024 Checkmk GmbH - License: Checkmk Enterprise License
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->

<script setup lang="ts">
import { ref } from 'vue'

import CmkIcon from '@/components/CmkIcon.vue'

import { type Topic } from '@/graph-designer/type_defs'

const props = defineProps<{
  topics: Topic[]
}>()

const hiddenTopics = ref<Record<string, boolean>>({})

function toggleTopic(topic: Topic) {
  hiddenTopics.value[topic.ident] = !hiddenTopics.value[topic.ident]
}

function getClass(ident: string) {
  return {
    open: !hiddenTopics.value[ident],
    closed: hiddenTopics.value[ident]
  }
}
</script>

<template>
  <div class="container">
    <table
      v-for="topic in props.topics"
      :key="topic.ident"
      class="nform"
      :class="getClass(topic.ident)"
    >
      <thead>
        <tr class="heading" @click="toggleTopic(topic)">
          <td colspan="2">
            <CmkIcon
              class="gd-topics-renderer__icon"
              :class="{ 'gd-topics-renderer__icon--open': !hiddenTopics[topic.ident] }"
              size="xxsmall"
              name="tree_closed"
            />
            {{ topic.title }}
          </td>
        </tr>
      </thead>
      <tbody :class="getClass(topic.ident)">
        <tr>
          <td colspan="2" />
        </tr>
        <template v-if="topic.customContent">
          <tr>
            <td colspan="2" class="custom-content">
              <slot :name="`${topic.ident}_custom`"></slot>
            </td>
          </tr>
        </template>
        <template v-else>
          <tr v-for="element in topic.elements" :key="element.ident">
            <td class="legend">
              <div class="title">
                {{ element.title }}
                <span class="dots">{{ Array(200).join('.') }}</span>
              </div>
            </td>
            <td class="content">
              <slot :name="element.ident"></slot>
            </td>
          </tr>
        </template>
        <tr class="bottom">
          <td colspan="2"></td>
        </tr>
      </tbody>
    </table>
  </div>
</template>

<style scoped>
.gd-topics-renderer__icon {
  margin-right: 10px;
  transition: transform 0.2s ease-in-out;
  transform: rotate(90deg);
}

.gd-topics-renderer__icon--open {
  transform: rotate(0deg);
}
</style>
