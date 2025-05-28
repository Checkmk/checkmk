<!--
Copyright (C) 2024 Checkmk GmbH - License: Checkmk Enterprise License
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->

<script setup lang="ts">
import { ref } from 'vue'
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
            <img class="vue nform treeangle" :class="getClass(topic.ident)" />
            {{ topic.title }}
          </td>
        </tr>
      </thead>
      <tbody :class="getClass(topic.ident)">
        <tr>
          <td colspan="2" />
        </tr>
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
        <tr class="bottom">
          <td colspan="2"></td>
        </tr>
      </tbody>
    </table>
  </div>
</template>
