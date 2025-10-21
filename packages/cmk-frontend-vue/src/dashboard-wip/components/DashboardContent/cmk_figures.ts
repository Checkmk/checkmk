/**
 * Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { WidgetContent } from '@/dashboard-wip/types/widget.ts'

/*
 * This is a wrapper class for the FigureBase implementation within cmk-frontend.
 * Calling this class instead of referencing the cmk-frontend code directly keeps other Vue files
 * clean, i.e. well-typed.
 *
 * TODO: Once we migrate the figure code from cmk-frontend to cmk-frontend-vue we can remove/extend
 * this file.
 */

export class FigureBase {
  // the correct type of instance would be FigureBase from the JS figures code
  instance

  constructor(
    figureType: string,
    divSelector: string,
    ajaxPage: string,
    postBody: string,
    figureSpec: WidgetContent,
    updateInterval: number
  ) {
    // @ts-expect-error comes from different javascript file
    const cmkToolkit = window['cmk']

    const registry = cmkToolkit.figures.figure_registry
    if (!registry) {
      console.error('Figure registry is not available.')
      return
    }

    const typeMap: Record<string, string> = {
      event_stats: 'eventstats',
      host_stats: 'hoststats',
      service_stats: 'servicestats',
      host_state: 'state_host',
      service_state: 'state_service'
    }
    function newToLegacyType(newType: string): string {
      if (newType in typeMap && typeMap[newType]) {
        return typeMap[newType]
      }
      return newType
    }
    const legacyFigureType: string = newToLegacyType(figureType)
    const figureCtor = registry.get_figure(legacyFigureType)
    this.instance = new figureCtor(divSelector)
    this.instance.set_post_url_and_body(ajaxPage, postBody)
    this.instance.set_dashlet_spec(figureSpec)
    this.instance.initialize()
    this.forceUpdate(updateInterval)

    return this
  }

  private forceUpdate(updateInterval?: number) {
    if (!this.instance) {
      return
    }
    if (typeof updateInterval === 'number' && !isNaN(updateInterval)) {
      this.instance.scheduler.set_update_interval(updateInterval)
      this.instance.scheduler.enable()
    } else {
      this.instance.scheduler.force_update()
    }
  }

  public update(ajaxPage: string, postBody: string, figureSpec: WidgetContent) {
    this.instance.set_post_url_and_body(ajaxPage, postBody)
    this.forceUpdate() // running the scheduler and fetching data
    this.instance.set_dashlet_spec(figureSpec)
    this.instance.update_gui()
  }

  public disable() {
    if (this.instance && this.instance.scheduler) {
      this.instance.scheduler.disable()
    }
  }

  public resize() {
    if (this.instance && this.instance.resize) {
      this.instance.resize()
    }
  }

  public update_gui() {
    if (this.instance && this.instance.update_gui) {
      this.instance.update_gui()
    }
  }
}
