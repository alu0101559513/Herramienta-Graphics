from typing import Annotated

from bson import ObjectId
from bson.errors import InvalidId
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from server.core.security import decode_access_token
from server.models.user import User

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/token")


def get_credentials_exception() -> HTTPException:
    """
    Description:
        Build the standard authentication exception used when a request does not
        contain valid Bearer credentials.

    Args:
        None.

    Returns:
        HTTPException:
            HTTP 401 exception with the Bearer authentication header.
    """

    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Not authenticated",
        headers={"WWW-Authenticate": "Bearer"},
    )


async def get_authenticated_user(
    token: Annotated[str, Depends(oauth2_scheme)],
) -> User:
    """
    Description:
        Resolve the authenticated user from a Bearer access token.

        The token is decoded, its subject claim is read as a MongoDB ObjectId,
        and the corresponding user document is loaded from the database.

    Args:
        token (str):
            Access token extracted from the Authorization header by FastAPI's
            OAuth2PasswordBearer dependency.

    Returns:
        User:
            Authenticated user document.

    Raises:
        HTTPException:
            Raised with HTTP 401 when the token is missing, invalid, does not
            contain a valid subject, or references a user that no longer exists.
    """

    payload = decode_access_token(token)

    if not payload:
        raise get_credentials_exception()

    user_id = payload.get("sub")

    if not user_id:
        raise get_credentials_exception()

    try:
        object_id = ObjectId(user_id)
    except InvalidId as exc:
        raise get_credentials_exception() from exc

    user = await User.get(object_id)

    if not user:
        raise get_credentials_exception()

    return user
