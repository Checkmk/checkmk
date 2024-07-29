<script setup lang="ts">
// eslint-disable-next-line
// @ts-nocheck
import { type TableCell, type TableRow, type VueTableSpec } from '@/types'
import { ref, onMounted } from 'vue'
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
      if (content.type == 'text') {
        combined_text.push(content.content!.toLowerCase())
      }
    })
  })
  return combined_text.join('#')
})

function get_rows(): TableRow[] {
  const search_value = search_text.value.toLowerCase()

  function get_custom_filter(search_text: string) {
    return function customFilter(value: string) {
      return value.includes(search_text)
    }
  }

  if (search_value) {
    search_text_dimension.filterFunction(get_custom_filter(search_value))
  } else {
    search_text_dimension.filterAll()
  }
  let records = row_crossfilter.allFiltered()

  function get_custom_sorter_function(index: number, direction: number) {
    return function (a: TableRow, b: TableRow) {
      const a_content = a.columns[index].content[0]!.content!.toLowerCase()
      const b_content = b.columns[index].content[0]!.content!.toLowerCase()
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
  return records as TableRow[]
}

function replace_inpage_search() {
  const search_form = d3.select('#form_inpage_search_form')
  search_form.selectAll('input:not(.text)').remove()
  search_form.selectAll('input').on('keyup', (event) => {
    search_text.value = event.target.value
    update_d3js_table()
  })
  d3.select('#page_menu_popups')
    .append('div')
    .html(
      '<label class="input-sizer"><input  type="text" size="1" onInput="this.parentNode.dataset.value = this.value" placeholder="blafasel"></label>'
    )
}

onMounted(() => {
  console.log('table on mounted')
  row_crossfilter.add(props.tableSpec.rows)
  force_render.value += 1
  replace_inpage_search()
  update_d3js_table()
})

let current_sort_index: null | [number, number] = null

function set_sort_index(index: number) {
  if (current_sort_index == null || current_sort_index[0] != index) {
    current_sort_index = [index, 1]
  } else if (current_sort_index[0] == index) {
    current_sort_index = [index, current_sort_index[1] * -1]
  }
  force_render.value += 1
  update_d3js_table()
}

const d3_anchor = ref<HTMLDivElement | undefined>()

function update_d3js_table() {
  if (d3_anchor.value == undefined) {
    return
  }

  const update_start = performance.now()

  // table/tbody
  const root_div = d3.select(d3_anchor.value)
  const table = root_div
    .selectAll<HTMLTableElement, VueTableSpec>('table')
    .data([props.tableSpec])
    .join('table')
  const tbody = table.join('tbody').attr('class', props.tableSpec.classes.join(' '))

  // Headers
  const header_row = tbody
    .selectAll<HTMLTableRowElement, string[]>('tr.header')
    .data((d) => [d.headers])
    .join('tr')
    .classed('header', true)
  header_row
    .selectAll<HTMLTableCellElement, string>('th')
    .data((d) => d)
    .join('th')
    .text((d) => d)
    .each((d, idx, nodes) => {
      d3.select(nodes[idx]).on('click', () => set_sort_index(idx))
    })

  // Data rows
  const data_rows = tbody
    .selectAll<HTMLTableRowElement, TableRow>('tr.data')
    .data(get_rows(), (d) => {
      return d.key
    })
  data_rows.exit().remove()
  const new_rows = data_rows
    .enter()
    .append('tr')
    .attr('class', (d) => d.classes.join(' '))
    .classed('data', true)

  // Cells contents
  const new_cells = new_rows
    .selectAll<HTMLTableCellElement, TableCell>('td')
    .data((d) => {
      return d.columns
    })
    .join('td')
  data_rows.order()
  fill_td_cells(new_cells)
  console.log('update table took ', performance.now() - update_start)
}

function fill_td_cells(
  all_cells: d3.Selection<HTMLTableCellElement, TableCell, HTMLTableRowElement, TableRow>
) {
  all_cells.each(function (cell_data) {
    const td_node = d3.select(this)
    cell_data.content.forEach((content) => {
      switch (content.type) {
        case 'text':
          td_node.append('span').text(content.content!)
          break
        case 'html':
          td_node.append('span').html(content.content!)
          break
        case 'button':
          td_node
            .append('a')
            .attr('href', content.url!)
            .attr('title', content.title!)
            .append('img')
            .attr('class', 'icon iconbutton')
            .attr('src', content.icon!)
          break
        case 'checkbox':
          td_node.append('input').attr('type', 'checkbox').classed('vue_checkbox', true)
          break
        case 'href':
          td_node.append('a').attr('href', content.url!).text(content.alias!)
          break
      }
    })
  })
}
</script>

<template>
  <label>D3JS Table</label>
  <div ref="d3_anchor" />
  <label class="input-sizer"> </label>
</template>
