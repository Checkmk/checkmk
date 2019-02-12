((c++-mode . ((flycheck-cppcheck-suppressions . ("passedByValue"))))
 (python-mode . ((eval setq flycheck-python-mypy-executable
                       (concat (projectile-locate-dominating-file default-directory dir-locals-file)
                               "tests/static/run_mypy"))))
 (scss-mode . ((eval setq flycheck-sass/scss-sass-lint-executable
                     (concat (projectile-locate-dominating-file default-directory dir-locals-file)
                             "node_modules/.bin/sass-lint"))))
 )
