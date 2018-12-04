((c++-mode . ((flycheck-cppcheck-suppressions . ("passedByValue"))))
 (python-mode . ((eval . (setq flycheck-python-mypy-executable
                               (concat (locate-dominating-file default-directory dir-locals-file)
                                       "tests/static/.venv/bin/mypy"))))))
