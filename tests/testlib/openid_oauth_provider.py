#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import base64
from binascii import unhexlify
from dataclasses import dataclass
from typing import Annotated, Sequence
from urllib.parse import urlencode

import fastapi as fapi
import jwt
from cryptography.hazmat.primitives.asymmetric import rsa
from pydantic import BaseModel

from cmk.gui.cse.userdb.cognito.oauth2 import load_config, TenantInfo, UserRoleAnswer

application = fapi.FastAPI()


@application.get("/healthz", status_code=200, responses={200: {}})
def liveliness() -> str:
    return "I'm alive"


@dataclass(frozen=True)
class Config:
    base_url: str


def read_config() -> Config:
    import os

    return Config(base_url=os.environ["URL"])


class WellKnownReponseModel(BaseModel):
    authorization_endpoint: str
    token_endpoint: str
    jwks_uri: str
    issuer: str = "checkmk"
    scopes_supported: Sequence[str] = ["openid", "email"]
    response_types_supported: Sequence[str] = ["code", "token"]
    id_token_signing_alg_values_supported: Sequence[str] = ["RS256"]
    subject_types_supported: Sequence[str] = ["public"]
    token_endpoint_auth_methods_supported: Sequence[str] = ["client_secret_post"]
    grant_types_supported: Sequence[str] = ["authorization_code"]


@application.get("/.well-known/openid-configuration", status_code=200)
def well_known(config: Config = fapi.Depends(read_config)) -> WellKnownReponseModel:
    return WellKnownReponseModel(
        authorization_endpoint=f"{config.base_url}/authorize",
        jwks_uri=f"{config.base_url}/.well-known/jwks.json",
        token_endpoint=f"{config.base_url}/token",
    )


class JWKS:
    def __init__(self) -> None:
        self.private = rsa.generate_private_key(public_exponent=65537, key_size=1024)
        self.public = self.private.public_key()
        self.kid = "usethis"

    @property
    def n(self) -> str:
        n = self.public.public_numbers().n
        hexi = hex(n).lstrip("0x")
        encoded = base64.urlsafe_b64encode(unhexlify(hexi))
        return encoded.decode("utf-8").rstrip("=")


KEY = JWKS()


class KeyModel(BaseModel):
    n: str
    alg: str = "RS256"
    e: str = "AQAB"
    kid: str
    use: str = "sig"
    kty: str = "RSA"


class JWKSModel(BaseModel):
    keys: Sequence[KeyModel]


@application.get("/.well-known/jwks.json", response_model=JWKSModel)
def jwks() -> JWKSModel:
    key = KeyModel(n=KEY.n, kid=KEY.kid)
    return JWKSModel(keys=[key])


class TokenResponse(BaseModel):
    id_token: str


class TokenPayload(BaseModel):
    email: str
    aud: str
    sub: str = "1234567"


@application.post("/token", response_model=TokenResponse)
def token(client_id: Annotated[str, fapi.Form()]) -> TokenResponse:
    payload = TokenPayload(email="test@test.com", aud=client_id)
    id_token = jwt.encode(
        payload.model_dump(), KEY.private, algorithm="RS256", headers={"kid": KEY.kid}
    )
    return TokenResponse(id_token=id_token)


@application.get("/authorize")
def authorize(state: str, redirect_uri: str) -> fapi.responses.RedirectResponse:
    params = {"state": state, "code": "fake"}
    url = f"{redirect_uri}?{urlencode(params)}"
    return fapi.responses.RedirectResponse(url)


# this endpoint is used by checkmk to authorize the user on a site
# given he belongs to the right tenant
@application.get("/api/users/{user_id}/tenants")
def tenant_role_mapping(user_id: str) -> UserRoleAnswer:
    config = load_config()
    tenant_info = TenantInfo(user_role="admin")
    return UserRoleAnswer(tenants={config.tenant_id: tenant_info})
