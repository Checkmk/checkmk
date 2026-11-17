/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { restApiHttp } from 'cmk-ui-library/vitest.msw'

/** Answers the title request of a widget wizard preview, which shows the widget under the title. */
export function widgetTitlesHandler(title: string) {
  return restApiHttp.post(
    '/domain-types/dashboard/actions/compute-widget-titles/invoke',
    ({ response }) =>
      response(200).json({
        domainType: 'dashboard-widget-titles',
        id: 'titles',
        links: [],
        extensions: { titles: { preview_widget: title } }
      })
  )
}

/** Answers the attributes request of a widget wizard preview with a widget that uses no infos. */
export function widgetAttributesHandler() {
  return restApiHttp.post(
    '/domain-types/dashboard/actions/compute-widget-attributes/invoke',
    ({ response }) =>
      response(200).json({
        domainType: 'widget-compute',
        value: { filter_context: { uses_infos: [] } }
      })
  )
}
