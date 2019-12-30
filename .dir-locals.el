((c++-mode . ((flycheck-cppcheck-suppressions . ("passedByValue"))))
 (python-mode . ((eval setq flycheck-python-mypy-executable
                       (concat (projectile-locate-dominating-file default-directory dir-locals-file)
                               "scripts/run-mypy"))
                 (eval setq flycheck-python-pylint-executable
                       (concat (projectile-locate-dominating-file default-directory dir-locals-file)
                           "scripts/run-pylint"))
                 (eval eval-after-load "yapfify"
                     '(defun yapfify-call-bin (input-buffer output-buffer start-line end-line)
                          "Call process yapf on INPUT-BUFFER saving the output to OUTPUT-BUFFER.

Return the exit code.  START-LINE and END-LINE specify region to
format."
                          (with-current-buffer input-buffer
                              (call-process-region (point-min) (point-max)
                                  (concat (projectile-locate-dominating-file default-directory dir-locals-file)
                                      "scripts/run-pipenv")
                                  nil output-buffer nil
                                  (if (string-suffix-p "python3\n" (save-excursion (goto-char (point-min)) (thing-at-point 'line t))) "3" "2")
                                  "run" "yapf"
                                  "-l" (concat (number-to-string start-line) "-" (number-to-string end-line))))))))
 (scss-mode . ((eval setq flycheck-sass/scss-sass-lint-executable
                     (concat (projectile-locate-dominating-file default-directory dir-locals-file)
                             "node_modules/.bin/sass-lint"))))
 )
