# cmk-frontend-vue

Checkmk vue experiments

## development

```sh
./run --all
```

### trying out changes in a site

#### f12

f12 is working, but is using the production ready build process and therefore not
super fast (currently six seconds)

#### vite dev server

To combine both the vite auto hot reload and the site, the proxy feature of the
vite dev server is used.

* run `npm run dev`
* surf to `http://localhost:5173/<yoursite>/check_mk/` (tailing slash is
  important, otherwise checkmk will redirect to a url without the port)
* enable "Inject cmk-frontend-vue files via vite client" in "User Interface"
  in "Experimental Features" in "global settings"

Checkmk should then automatically reload as soon as you change a file of the
cmk-frontend-vue project.

### testing components outsite a site

* run `npm ci` in this folder, and also in `../cmk-frontend`
    * yes, we should not need to execute `npm ci` in another package, but this
      is the current reality: the code in `cmk-frontend-vue` is not really
      independent of `cmk-frontend`. The styling of `cmk-frontend` is necessary
      for many `FormEdit` sub-components.
* run `npm run -- dev --config vite.config.demo.ts`
* surf to `http://localhost:5173/`


### Location of files and folders
src/
    form/  # files for form rendering
        index.ts     # Includes exports. E.g FormApp, ValiationMessages
        FormApp.vue  # Main entry point
        components/  # Files for the forms feature
            utils/   # Utilities for forms
            forms/   # Implementation of forms
            FormEdit.vue
            FormReadonly.vue
            FormHelp.vue
            FormValidation.vue
    quick-setup/
        QuickSetupApp.vue # Main entry point
        components/  # Files for the quick-setup feature
            widgets/
            elements/
            QuickSetupStage.vue
            ...
    global-settings/ # upcoming: global settings rendering
        GlobalSettingsApp.vue
        components/  # Files for the global-setting feature
    graph-designer/  # upcoming: reworked graph designer
        GraphDesignerApp.vue
        components/  # Files for the graph-designer feature
    notification/
        NotificationOverviewApp.vue  # Overview page for notifications
        NotificationParametersOverviewApp.vue # Overview page for notification parameter
        components/
            CoreStats.vue  # Core statistics on notification overview page
            FallbackWarning.vue  # Warning about missing fallback Email address on notification overview page
            NotificationRules.vue  # Notification rule list on notification overview page
            NotificationStats.vue  # Notification statistics on notification overview page
