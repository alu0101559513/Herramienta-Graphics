import re

from pydantic import BaseModel, EmailStr, Field, field_validator


def validate_password_rules(password: str) -> str:
    """
    Description:
        Validate password strength according to security rules.

    Args:
        password (str): Password to validate.

    Returns:
        str: Validated password if all rules are satisfied.
    """

    if len(password) < 8:
        raise ValueError("Password must be at least 8 characters")

    if not re.search(r"[A-Z]", password):
        raise ValueError("Password must contain an uppercase letter")

    if not re.search(r"[a-z]", password):
        raise ValueError("Password must contain a lowercase letter")

    if not re.search(r"\d", password):
        raise ValueError("Password must contain a number")

    return password


class RegisterRequest(BaseModel):
    """
    Description:
        Payload used to register a new user account.

    Args:
        None.

    Returns:
        RegisterRequest: Pydantic request model.
    """

    username: str = Field(min_length=3, max_length=50)
    email: EmailStr
    password: str

    @field_validator("username")
    @classmethod
    def normalize_username(cls, username: str) -> str:
        """
        Description:
            Normalize username before registration.

        Args:
            username (str): Raw username.

        Returns:
            str: Trimmed and lowercase username.
        """

        return username.strip().lower()

    @field_validator("password")
    @classmethod
    def validate_password(cls, password: str) -> str:
        """
        Description:
            Apply password validation rules during registration.

        Args:
            password (str): Password value to validate.

        Returns:
            str: Validated password.
        """

        return validate_password_rules(password)


class LoginRequest(BaseModel):
    """
    Description:
        Payload used to authenticate with username and password.

    Args:
        None.

    Returns:
        LoginRequest: Pydantic request model.
    """

    username: str
    password: str

    @field_validator("username")
    @classmethod
    def normalize_username(cls, username: str) -> str:
        """
        Description:
            Normalize username before login.

        Args:
            username (str): Raw username.

        Returns:
            str: Trimmed and lowercase username.
        """

        return username.strip().lower()


class TokenResponse(BaseModel):
    """
    Description:
        Response model that carries the issued access token.

    Args:
        None.

    Returns:
        TokenResponse: Pydantic response model.
    """

    access_token: str
    token_type: str = "bearer"


class UpdateUserRequest(BaseModel):
    """
    Description:
        Payload used to update profile fields for the current user.

    Args:
        None.

    Returns:
        UpdateUserRequest: Pydantic request model.
    """

    username: str | None = Field(default=None, min_length=3, max_length=50)
    email: EmailStr | None = None

    @field_validator("username")
    @classmethod
    def normalize_username(cls, username: str | None) -> str | None:
        """
        Description:
            Normalize username before profile update.

        Args:
            username (str | None): Raw username.

        Returns:
            str | None: Trimmed and lowercase username or None.
        """

        if username is None:
            return None

        return username.strip().lower()


class ChangePasswordRequest(BaseModel):
    """
    Description:
        Payload used to change the current user's password.

    Args:
        None.

    Returns:
        ChangePasswordRequest: Pydantic request model.
    """

    current_password: str
    new_password: str

    @field_validator("new_password")
    @classmethod
    def validate_new_password(cls, password: str) -> str:
        """
        Description:
            Apply password validation rules to the new password.

        Args:
            password (str): New password value to validate.

        Returns:
            str: Validated password.
        """

        return validate_password_rules(password)
