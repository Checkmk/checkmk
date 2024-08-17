# cmk-frontend-vue

Checkmk vue experiments

## development

```sh
./run --setup-environment
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

### Location of files and folders
src/
    form/  # files for form rendering
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
    index.ts         # Provides exports for the different apps, e.g FormApp, QuicksetupApp
