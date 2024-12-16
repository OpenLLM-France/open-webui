import logging
import uuid
import jwt

from datetime import UTC, datetime, timedelta
from typing import Optional, Union, List, Dict

from open_webui.apps.webui.models.users import Users

from open_webui.constants import ERROR_MESSAGES
from open_webui.env import SRC_LOG_LEVELS, WEBUI_SECRET_KEY, LITELLM_HOST, LITELLM_MASTER_KEY

from fastapi import Depends, HTTPException, Request, Response, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from passlib.context import CryptContext
import requests


log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["MODELS"])


SESSION_SECRET = WEBUI_SECRET_KEY
ALGORITHM = "HS256"

##############
# Auth Utils
##############

bearer_security = HTTPBearer(auto_error=False)
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def verify_password(plain_password, hashed_password):
    return (
        pwd_context.verify(plain_password, hashed_password) if hashed_password else None
    )


def get_password_hash(password):
    return pwd_context.hash(password)


def create_token(data: dict, expires_delta: Union[timedelta, None] = None) -> str:
    payload = data.copy()

    if expires_delta:
        expire = datetime.now(UTC) + expires_delta
        payload.update({"exp": expire})

    encoded_jwt = jwt.encode(payload, SESSION_SECRET, algorithm=ALGORITHM)
    return encoded_jwt

def generate_llm_api_key(email, user_name):
    url = f"{LITELLM_HOST}/key/generate"
    headers = {
        "Authorization": f"Bearer {LITELLM_MASTER_KEY}",
        "Content-Type": "application/json"
    }

    # TODO: Other things can be setted up, depending on the offer & pricing: Duration, etc. We can define a Pydantic Model for each offer for better modeling
    data = {
        "metadata": {"user": f"{user_name}"},
        'max_budget': 10,
        'budget_duration': '1h',
        'key_alias': f"{user_name}",

        'metadata': {"team": "AiTeam", "user":user_name, "email": email}
        # "models": ["gpt-3.5-turbo", "gpt-4"], all models will be exposed. TODO: Eventually, we can set it up
    }

    response = requests.post(url, headers=headers, json=data)

    # Check the response
    if response.status_code == 200:
        response_data = response.json()
        litellm_api_key = response_data.get("key")
        log.info(f"Generated key: {litellm_api_key}")
        return litellm_api_key
    else:
        raise Exception(f"Error at key generation: {response.status_code}, {response.json()}")

def decode_token(token: str) -> Optional[dict]:
    try:
        decoded = jwt.decode(token, SESSION_SECRET, algorithms=[ALGORITHM])
        return decoded
    except Exception:
        return None


def extract_token_from_auth_header(auth_header: str):
    return auth_header[len("Bearer ") :]


def create_api_key():
    key = str(uuid.uuid4()).replace("-", "")
    return f"sk-{key}"


def get_http_authorization_cred(auth_header: str):
    try:
        scheme, credentials = auth_header.split(" ")
        return HTTPAuthorizationCredentials(scheme=scheme, credentials=credentials)
    except Exception:
        raise ValueError(ERROR_MESSAGES.INVALID_TOKEN)


def get_current_user(
    request: Request,
    auth_token: HTTPAuthorizationCredentials = Depends(bearer_security),
):
    token = None

    if auth_token is not None:
        token = auth_token.credentials

    if token is None and "token" in request.cookies:
        token = request.cookies.get("token")

    if token is None:
        raise HTTPException(status_code=403, detail="Not authenticated")

    # auth by api key
    if token.startswith("sk-"):
        if not request.state.enable_api_key:
            raise HTTPException(
                status.HTTP_403_FORBIDDEN, detail=ERROR_MESSAGES.API_KEY_NOT_ALLOWED
            )
        return get_current_user_by_api_key(token)

    # auth by jwt token
    try:
        data = decode_token(token)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
        )

    if data is not None and "id" in data:
        user = Users.get_user_by_id(data["id"])
        if user is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=ERROR_MESSAGES.INVALID_TOKEN,
            )
        else:
            Users.update_user_last_active_by_id(user.id)
        return user
    else:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ERROR_MESSAGES.UNAUTHORIZED,
        )


def get_current_user_by_api_key(api_key: str):
    user = Users.get_user_by_api_key(api_key)

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ERROR_MESSAGES.INVALID_TOKEN,
        )
    else:
        Users.update_user_last_active_by_id(user.id)

    return user


def get_verified_user(user=Depends(get_current_user)):
    if user.role not in {"user", "admin"}:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ERROR_MESSAGES.ACCESS_PROHIBITED,
        )
    return user


def get_admin_user(user=Depends(get_current_user)):
    if user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ERROR_MESSAGES.ACCESS_PROHIBITED,
        )
    return user
