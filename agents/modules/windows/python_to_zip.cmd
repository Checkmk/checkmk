@rem Wrapper to zip python, also reference
@cd %1
@7z a -r -tzip -y -stl -mmt4 %2 *.*
