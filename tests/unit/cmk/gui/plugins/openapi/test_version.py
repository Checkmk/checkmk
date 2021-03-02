import pytest   # type: ignore[import]

from cmk.utils import version

managedtest = pytest.mark.skipif(not version.is_managed_edition(), reason="see #7213")
