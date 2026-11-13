## Drill-down and drill-up

- A click on an element of a widget, such as a host in a list, can open a view
  or a dashboard filtered to that element.
- The page reached this way offers a way back to the page the click came from.

### Contextual links

- A widget's _contextual link_ decides where a click on one of its elements
  leads.
- Its mode is `none`, `default`, `inherited` or `custom`.
- `none` links nowhere.
- `default` links to the widget type's built-in target.
- `inherited` links to one view or dashboard and carries only what the clicked
  element identifies.
- `custom` offers one or more links, each to a view or dashboard with its own
  filters.
- A link can also carry the widget's effective filter context.
- A link can also carry the dashboard's time range.
- A link names its target, and each viewer opens the copy that name resolves to
  for them.
- The modes and filters a widget type offers follow from the type of its
  `contextual_link` field in the API model.

Code:

- `api/model/contextual_link.py`: the modes, the offered options and the
  validation

### The filters a link carries

- Each filter a link carries is valued from the clicked element, for example
  its site, host name or service state.
- Which filters a click can value depends on what was clicked: one host, one
  service, or an aggregate of hosts or services.
- A filter the element cannot value is dropped.
- If the link carries the effective filter context and that context has the
  filter, the filter travels from there and is not dropped.
- If the element lacks one key of a filter, only that key is dropped.
- A deferred filter is valued only when the link is opened.
- The URL tells the target page which filters were dropped and why.

Code:

- `api/model/context_filters.py`: the filters for each kind of click

### Link URLs

- With each element, the compute endpoint returns the encoded filter values for
  each of the widget's links.
- The browser builds the URL of the target page from them.
- A filter valued from the clicked element replaces the same filter from the
  effective filter context.

Code:

- `api/_contextual_link_encoding.py`: the encoded filter values of an element
- `lib/contextualLinkUrl.ts`: the URL of the target page

### Column links of embedded views

- Each column of an embedded view can link to a view or dashboard as well.
- The backend builds these URLs while it renders the view, from the row of the
  clicked cell.

Code:

- `view_drilldown.py`: the URLs of the column links

### Drill-up

- A drill-down URL carries the title of the page it left.
- The target page then shows a button back to that page in its header.
- The button goes back in the tab's history.
- If the drill-down opened a new tab, the button leads to the referring page of
  the same site instead.
- Without either, the page shows no button.
- For a column link in an embedded view, the dashboard hands the view its own
  URL, so the way back leads to the dashboard.

Code:

- `cmk/gui/top_heading.py`: adds the button to the target page
- `packages/cmk-frontend-vue/src/page-header/drillUp.ts`: where the button
  leads

### Giving a widget type contextual links

1. Type the content model's `contextual_link` field with `ContextualLinkSpec`
   and the filters its clicks can value, or with
   `TargetlessContextualLinkSpec` if the type has no built-in target.
2. Pass the widget type's built-in link, or `no_built_in_link`, to
   `resolve_widget` in the compute endpoint.
3. Build the compute endpoint with `link_targets=True`.
4. Return the widget's links, and each element's link properties from
   `link_properties_for`.
5. In the frontend, wrap each clickable element in `ContextualLinkTrigger`.

Code:

- `api/compute_stats.py`: steps 2 to 4 for the statistics widgets
- `components/figures/CmkStatsFigure.vue`: step 5 for the same widgets
