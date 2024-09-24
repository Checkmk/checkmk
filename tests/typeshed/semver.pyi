import semver

# Only what I need now, sorry. semver 3.0.0 will bring type annotations.
class VersionInfo:
    def __init__(
        self,
        major: int,
        minor: int = 0,
        patch: int = 0,
        prerelease: str | None = None,
        build: str | None = None,
    ) -> None: ...
    @classmethod
    def parse(cls, version: str) -> semver.VersionInfo: ...
    @property
    def major(self) -> int: ...
    @property
    def minor(self) -> int: ...
