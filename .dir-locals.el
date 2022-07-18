((nil . (
         (grep-find-ignored-files . (
         "*.min.js" "*.standalone.js" "*.map" "*.gz" ".#*" "*.o" "*~" "*.bin"
         "*.lbin" "*.so" "*.a" "*.ln" "*.blg" "*.bbl" "*.elc" "*.lof"
         "*.glo" "*.idx" "*.lot" "*.fmt" "*.tfm" "*.class" "*.fas"
         "*.lib" "*.mem" "*.x86f" "*.sparcf" "*.dfsl" "*.pfsl"
         "*.d64fsl" "*.p64fsl" "*.lx64fsl" "*.lx32fsl" "*.dx64fsl"
         "*.dx32fsl" "*.fx64fsl" "*.fx32fsl" "*.sx64fsl" "*.sx32fsl"
         "*.wx64fsl" "*.wx32fsl" "*.fasl" "*.ufsl" "*.fsl" "*.dxl"
         "*.lo" "*.la" "*.gmo" "*.mo" "*.toc" "*.aux" "*.cp" "*.fn"
         "*.ky" "*.pg" "*.tp" "*.vr" "*.cps" "*.fns" "*.kys" "*.pgs"
         "*.tps" "*.vrs" "*.pyc" "*.pyo"))
         (grep-find-ignored-directories . (
           ".git" ".venv" "node_modules" ".mypy_cache" ".pytest_cache"
	   "SCCS" "RCS" "CVS" "MCVS" ".src" ".svn" ".git" ".hg" ".bzr" "_MTN" "_darcs" "{arch}"))
         ))
 (c++-mode . ((flycheck-cppcheck-suppressions . ("passedByValue"))))
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
                                  "run" "yapf"
                                  "-l" (concat (number-to-string start-line) "-" (number-to-string end-line))))))))
 )
