/**
 * Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { Selection } from 'd3'
import { select } from 'd3'

export class TabsBar {
  _div_selector: string
  _div_selection: Selection<HTMLDivElement, unknown, HTMLElement, any>
  _tabs_by_id: Record<string, Tab>
  _tabs_list: Tab[]
  _nav!: Selection<HTMLElement, unknown, HTMLElement, any>
  main_content!: Selection<HTMLDivElement, unknown, HTMLElement, any>
  _ul!: Selection<HTMLUListElement, unknown, HTMLElement, any>
  constructor(div_selector: string) {
    this._div_selector = div_selector
    this._div_selection = select<HTMLDivElement, unknown>(this._div_selector)
    this._div_selection.classed('cmk_tab', true)
    this._tabs_by_id = {}
    this._tabs_list = []
  }
  initialize(_tab?: string, _ifid?: string, _vlanid?: string) {
    this._nav = this._div_selection
      .append('nav')
      .attr('role', 'navigation')
      .classed('main-navigation', true)
    this.main_content = this._div_selection.append('div').classed('main-content', true)

    this._register_tabs()

    this._ul = this._nav.append('ul')
    const a_selection = this._ul
      .selectAll('li')
      .data(this._tabs_list)
      .enter()
      .append('li')
      .each((d, idx, nodes) => {
        select(nodes[idx]).classed(d.tab_id(), true)
      })
      .on('click', (event) => this._tab_clicked(event))
      .append('a')
      .attr('href', (d) => '#' + d.tab_id())
      .style('pointer-events', 'none')

    a_selection
      .append('span')
      .classed('noselect', true)
      .text((d) => d.name())
  }

  _register_tabs() {
    this._get_tab_entries().forEach((tab_class) => {
      const new_tab = new tab_class(this)
      new_tab.initialize()
      this._tabs_by_id[new_tab.tab_id()] = new_tab
      this._tabs_list.push(new_tab)
    })
  }

  get_tab_by_id(tab_id: string) {
    return this._tabs_by_id[tab_id]
  }

  _get_tab_entries(): (new (tabs_bar: any) => Tab)[] {
    return []
  }

  _tab_clicked(event: MouseEvent) {
    const target = select<HTMLElement, Tab>(event.target as HTMLElement)
    const tab = target.datum()
    this._activate_tab(tab)
  }

  _activate_tab(tab: Tab) {
    const enable_tab_id = tab.tab_id()

    // Hide all tabs
    this._ul.selectAll('li').classed('active', false)
    this.main_content.selectAll('.cmk_tab_element').classed('active', false)

    // Deactivate other tabs
    for (const tab_id in this._tabs_list) {
      if (tab_id == enable_tab_id) continue

      this._tabs_list[tab_id].deactivate()
    }

    // Enable selected tab
    this._ul.select('li.' + enable_tab_id).classed('active', true)
    this.main_content.select('#' + enable_tab_id).classed('active', true)
    tab.activate()
  }
}

export abstract class Tab<T extends TabsBar = TabsBar> {
  _tabs_bar: T
  _tab_selection: Selection<HTMLDivElement, any, HTMLElement, any>
  _link_item!: Selection<HTMLAnchorElement, any, HTMLElement, any>
  protected constructor(tabs_bar: T) {
    this._tabs_bar = tabs_bar
    this._tab_selection = tabs_bar.main_content
      .append('div')
      .attr('id', this.tab_id())
      .classed('cmk_tab_element', true)
      .datum(this)
  }

  // Internal ID
  abstract tab_id(): string

  // Name in tab index
  abstract name(): string

  // Called upon instance creation
  abstract initialize(): any

  // Called when the tab is activated
  abstract activate(): any

  // Called when the tab is deactivated
  abstract deactivate(): any
}
