<script setup lang="ts">
import { type TableRow, type VueTableSpec } from '@/types'
import { ref, onMounted, onBeforeUpdate, onUpdated } from 'vue'
import crossfilter from 'crossfilter2'
import * as d3 from 'd3'

/* eslint-disable @typescript-eslint/naming-convention */

const props = defineProps<{
  tableSpec: VueTableSpec
}>()

const search_text = ref<string>('')
const force_render = ref(0)

const row_crossfilter = crossfilter<TableRow>()
const search_text_dimension = row_crossfilter.dimension<string>((d: TableRow) => {
  let combined_text: string[] = []
  d.columns.forEach((column) => {
    column.content.forEach((content) => {
      // Might add additional types to this data dimension
      if (content.type == 'text') {
        combined_text.push(content.content!.toLowerCase())
      }
    })
  })
  return combined_text.join('#')
})

function replace_inpage_search() {
  const search_form = d3.select('#form_inpage_search_form')
  search_form.selectAll('input:not(.text)').remove()
  search_form.selectAll('input').on('keyup', (event) => {
    search_text.value = event.target.value
  })
}

function get_custom_filter(search_text: string) {
  return function customFilter(value: string) {
    return value.includes(search_text)
  }
}

function get_rows() {
  const search_value = search_text.value.toLowerCase()

  const use_crossfilter = true
  let records: TableRow[]
  if (!use_crossfilter) {
    records = []
    props.tableSpec.rows.forEach((row: TableRow) => {
      let found_match = false
      row.columns.forEach((column) => {
        column.content.forEach((content) => {
          if (content.type == 'text' && content.content!.includes(search_value)) {
            found_match = true
          }
        })
      })
      if (found_match) {
        records.push(row)
      }
    })
  } else {
    search_text_dimension.filterFunction(get_custom_filter(search_value))
    records = row_crossfilter.allFiltered()
  }

  function get_custom_sorter_function(index: number, direction: number) {
    return function (a: TableRow, b: TableRow) {
      const a_content = a.columns[index]!.content[0]!.content!.toLowerCase()
      const b_content = b.columns[index]!.content[0]!.content!.toLowerCase()
      if (a_content == b_content) {
        return 0
      }
      if (a_content > b_content) {
        return direction
      }
      return -direction
    }
  }

  if (current_sort_index != null) {
    records.sort(get_custom_sorter_function(current_sort_index[0], current_sort_index[1]))
  }
  return records
}

onMounted(() => {
  row_crossfilter.add(props.tableSpec.rows)
  force_render.value += 1
  replace_inpage_search()
})

let update_start = 0

onBeforeUpdate(() => {
  update_start = performance.now()
})

onUpdated(() => {
  console.log('Update took ', performance.now() - update_start)
})

let current_sort_index: null | [number, number] = null
function set_sort_index(index: number) {
  if (current_sort_index == null || current_sort_index[0] != index) {
    current_sort_index = [index, 1]
  } else if (current_sort_index[0] == index) {
    current_sort_index = [index, current_sort_index[1] * -1]
  }
  force_render.value += 1
}
</script>

<template>
  <label>VUE Table</label>
  <table :key="force_render" :class="tableSpec.classes">
    <tbody>
      <tr>
        <th
          v-for="(header, index) in tableSpec.headers"
          :key="index"
          @click="set_sort_index(index)"
        >
          {{ header }}
        </th>
      </tr>

      <tr v-for="row in get_rows()" :key="row.key" :class="row.classes">
        <!-- eslint-disable vue/require-v-for-key -->
        <td v-for="cell in row.columns" :class="cell.classes">
          <template v-for="content in cell.content">
            <input v-if="content.type === 'checkbox'" class="vue_checkbox" type="checkbox" />
            <a v-if="content.type === 'button'" :href="content.url!" :title="content.title!">
              <img class="icon iconbutton" :src="content.icon!" />
            </a>
            <span v-if="content.type === 'text'">{{ content.content }}</span>
            <!-- eslint-disable-next-line vue/no-v-html -->
            <span v-if="content.type === 'html'" v-html="content.content" />
            <a v-if="content.type === 'href'" :href="content.url!">{{ content.alias }}</a>
          </template>
        </td>
        <!-- eslint-enable -->
      </tr>
    </tbody>
  </table>
</template>
