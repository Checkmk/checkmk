Documentation
=============

Sphinx [AutoAPI](https://sphinx-autoapi.readthedocs.io/en/latest/index.html)
is used to generate documentation of `GUI end to end testing framework`.

The configuration of Sphinx AutoAPI can be seen within the [configuration file][./source/conf.py].
Follow the below mentioned instructions to generate HTML documentation

- Change directory to [docs](.).
- Run the command:
    ```bash
    sphinx-build source/ html/
    ```

The entrypoint for the documentation is present at [./html/index.html](./html/index.html).
