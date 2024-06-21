# cmk-frontend

Holds all theming, js and css source files.
The `dist` folder is the base for `~/share/check_mk/web/htdocs` in the site.

## webpack-watch

`npm run webpack-watch` is a a simple watch mode for js/css files.
To play together with a site its `etc/apache/conf.d/check_mk.conf` has
to be adapted. Either use the `-w` option of `omd-vonheute` or replace the
paths to `/omd/sites/*` in the following lines :

```
Alias /heute/check_mk /omd/sites/heute/share/check_mk/web/htdocs
<Directory /omd/sites/heute/share/check_mk/web/htdocs>
```

With the path to `packages/cmk-frontend/dist/` of your git (e.g.
`/home/aa/git/check_mk/packages/cmk-frontend/dist/`). After that `npm run
webpack-watch` you can run webpack in watch mode.
