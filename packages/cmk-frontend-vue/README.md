# cmk-frontend-vue

## Development

The run script and BUILD bazel file define the entry points to this
component, for example:

```sh
./run -h
./run --all
bazel run :vite [-- <ARGS>]
bazel run :vitest [-- <ARGS>]
```

## IDE Support

It's non trivial to set up bazel in such a way that js tooling will have
access to all required modules. The current suggested practice is to
create a local node_modules folder. Our tsconfig will fall back onto the
bazel workspace to find any modules provided by our repo.

To create a local node_modules folder, do:

```bash
bazel run -- @pnpm//:pnpm --dir $PWD install --frozen-lockfile
```

## Trying out changes in a site

### f12

f12 is working, but is using the production ready build process and
therefore not super fast (currently six seconds)

### Dev server

To combine both the vite auto hot reload and the site, the proxy feature of the
vite dev server is used.

To watch file changes across the bazelized components, you need to use
`ibazel` instead of `bazel`.

* download https://github.com/bazelbuild/bazel-watcher/releases/latest/download/ibazel_linux_amd64
  and add it to your path
* run `ibazel run :vite`
* surf to `http://localhost:5173/<yoursite>/check_mk/` (tailing slash is
  important, otherwise checkmk will redirect to a url without the port)
* enable "Inject cmk-frontend-vue files via vite client" in "User Interface"
  in "Experimental Features" in "global settings"

Checkmk should then automatically reload as soon as you change a file of the
cmk-frontend-vue project.

## Demo App

To try our reusable components outside a checkmk site, you can

* run `ibazel run :vite -- --config vite.config.demo.ts`
* surf to `http://localhost:5174/`


## Package management

If you need to change the dependencies you can do so by running pnpm
inside bazel, for example:

```sh
# Install package "foo"
bazel run -- @pnpm//:pnpm --dir $PWD install foo
# Update package "foo"
bazel run -- @pnpm//:pnpm --dir $PWD update foo
# Update lock file if package.json was edited manually
bazel run -- @pnpm//:pnpm --dir $PWD install --lockfile-only
```

If you add a new package, append a `":node_modules/<new-package>"` item
to the SRCS list in the `BUILD` file.
