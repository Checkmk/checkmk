from cmk.gui.exceptions import MKUnauthenticatedException
from cmk.gui.token_auth._store import TokenType


class MKTokenExpiredOrRevokedException(MKUnauthenticatedException):
    token_type: TokenType

    def __init__(self, *args: object, token_type: TokenType) -> None:
        super().__init__(*args)
        self.token_type: TokenType = token_type
