from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from server.core.security import create_access_token, hash_password, verify_password
from server.dependencies.auth import get_authenticated_user
from server.models.analysis import Analysis
from server.models.user import User
from server.schemas.auth import (
    ChangePasswordRequest,
    LoginRequest,
    RegisterRequest,
    TokenResponse,
    UpdateUserRequest,
)
from server.services.gridfs import delete_file

router = APIRouter(prefix="/auth", tags=["auth"])


def invalid_credentials_exception() -> HTTPException:
    """
    Description:
        Build the standard HTTP exception used for authentication failures.

    Args:
        None.

    Returns:
        HTTPException:
            Unauthorized error with the bearer authentication header set.
    """

    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )


async def authenticate_user(username: str, password: str) -> User | None:
    """
    Description:
        Authenticate a user using username and password.

    Args:
        username (str):
            Username submitted by the client.

        password (str):
            Plain-text password submitted by the client.

    Returns:
        User | None:
            Authenticated user when credentials are valid, otherwise None.
    """

    normalized_username = username.strip().lower()
    user = await User.find_one(User.username == normalized_username)

    if not user:
        return None

    if not verify_password(password, user.password_hash):
        return None

    return user


async def safe_delete_file(file_id: Any) -> None:
    """
    Description:
        Delete a GridFS file while suppressing storage errors.

        This is used during account deletion so one failed file deletion does not
        prevent the rest of the account cleanup from continuing.

    Args:
        file_id (Any):
            Stored file identifier.

    Returns:
        None.
    """

    if not file_id:
        return

    try:
        await delete_file(file_id)
    except Exception:
        pass


async def delete_nested_files(value: Any) -> None:
    """
    Description:
        Recursively delete file identifiers contained in nested structures.

        Analysis outputs may store file ids inside nested dictionaries and lists.
        This helper traverses those structures and attempts to delete every leaf
        value as a file id.

    Args:
        value (Any):
            Nested dictionary, list or direct file identifier.

    Returns:
        None.
    """

    if isinstance(value, dict):
        for nested_value in value.values():
            await delete_nested_files(nested_value)
        return

    if isinstance(value, list):
        for nested_value in value:
            await delete_nested_files(nested_value)
        return

    await safe_delete_file(value)


async def delete_analysis_files(analysis: Analysis) -> None:
    """
    Description:
        Delete all files associated with an analysis.

        This includes raw datasets, normalized datasets, metrics configuration,
        filtered datasets and generated outputs.

    Args:
        analysis (Analysis):
            Analysis document whose stored files should be removed.

    Returns:
        None.
    """

    await safe_delete_file(getattr(analysis, "raw_dataset_file_id", None))
    await safe_delete_file(getattr(analysis, "normalized_dataset_file_id", None))
    await safe_delete_file(getattr(analysis, "metrics_config_file_id", None))

    filtered_dataset_file_ids = getattr(analysis, "filtered_dataset_file_ids", {}) or {}

    for file_id in filtered_dataset_file_ids.values():
        await safe_delete_file(file_id)

    await delete_nested_files(getattr(analysis, "outputs", {}) or {})


@router.post("/register", status_code=status.HTTP_201_CREATED)
async def register(data: RegisterRequest) -> dict[str, Any]:
    """
    Description:
        Register a new user account.

    Args:
        data (RegisterRequest):
            Registration payload.

    Returns:
        dict[str, Any]:
            Created user summary.
    """

    normalized_username = data.username.strip().lower()
    normalized_email = data.email.strip().lower()

    existing_username = await User.find_one(User.username == normalized_username)

    if existing_username:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already exists",
        )

    existing_email = await User.find_one(User.email == normalized_email)

    if existing_email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already exists",
        )

    user = User(
        username=normalized_username,
        email=normalized_email,
        password_hash=hash_password(data.password),
    )

    await user.insert()

    return {
        "id": str(user.id),
        "username": user.username,
        "email": user.email,
        "created_at": user.created_at,
    }


@router.post("/login", response_model=TokenResponse)
async def login(data: LoginRequest) -> TokenResponse:
    """
    Description:
        Authenticate a user with JSON credentials and return an access token.

    Args:
        data (LoginRequest):
            Login credentials.

    Returns:
        TokenResponse:
            JWT access token response.
    """

    user = await authenticate_user(data.username, data.password)

    if not user:
        raise invalid_credentials_exception()

    return TokenResponse(access_token=create_access_token(user.id))


@router.post("/token", response_model=TokenResponse)
async def token_login(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
) -> TokenResponse:
    """
    Description:
        Authenticate a user using the OAuth2 password form flow.

        This route is useful for FastAPI OAuth2 tooling and clients expecting
        application/x-www-form-urlencoded login requests.

    Args:
        form_data (OAuth2PasswordRequestForm):
            OAuth2 username and password form data.

    Returns:
        TokenResponse:
            JWT access token response.
    """

    user = await authenticate_user(form_data.username, form_data.password)

    if not user:
        raise invalid_credentials_exception()

    return TokenResponse(access_token=create_access_token(user.id))


@router.get("/me")
async def me(
    user: Annotated[User, Depends(get_authenticated_user)],
) -> dict[str, Any]:
    """
    Description:
        Return the authenticated user's profile.

    Args:
        user (User):
            Current authenticated user.

    Returns:
        dict[str, Any]:
            Current user profile data.
    """

    return {
        "id": str(user.id),
        "username": user.username,
        "email": user.email,
        "created_at": user.created_at,
    }


@router.patch("/me")
async def update_user(
    data: UpdateUserRequest,
    user: Annotated[User, Depends(get_authenticated_user)],
) -> dict[str, str]:
    """
    Description:
        Update the authenticated user's username and/or email.

    Args:
        data (UpdateUserRequest):
            Profile update payload.

        user (User):
            Current authenticated user.

    Returns:
        dict[str, str]:
            Confirmation message.
    """

    if data.username is not None:
        normalized_username = data.username.strip().lower()

        existing = await User.find_one(
            User.username == normalized_username,
            User.id != user.id,
        )

        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username already exists",
            )

        user.username = normalized_username

    if data.email is not None:
        normalized_email = data.email.strip().lower()

        existing = await User.find_one(
            User.email == normalized_email,
            User.id != user.id,
        )

        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already exists",
            )

        user.email = normalized_email

    await user.save()

    return {"message": "User updated"}


@router.patch("/password")
async def change_password(
    data: ChangePasswordRequest,
    user: Annotated[User, Depends(get_authenticated_user)],
) -> dict[str, str]:
    """
    Description:
        Change the authenticated user's password.

    Args:
        data (ChangePasswordRequest):
            Current password and new password payload.

        user (User):
            Current authenticated user.

    Returns:
        dict[str, str]:
            Confirmation message.
    """

    if not verify_password(data.current_password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Current password incorrect",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user.password_hash = hash_password(data.new_password)

    await user.save()

    return {"message": "Password updated"}


@router.delete("/me")
async def delete_account(
    user: Annotated[User, Depends(get_authenticated_user)],
) -> dict[str, str]:
    """
    Description:
        Delete the authenticated user's account and all related analysis data.

        The cleanup removes analysis documents and attempts to delete every
        associated GridFS file before deleting the user.

    Args:
        user (User):
            Current authenticated user.

    Returns:
        dict[str, str]:
            Confirmation message.
    """

    try:
        analyses = await Analysis.find(Analysis.user_id == user.id).to_list()

        for analysis in analyses:
            await delete_analysis_files(analysis)
            await analysis.delete()

        await user.delete()

        return {"message": "Account deleted"}

    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete account: {str(exc)}",
        ) from exc
