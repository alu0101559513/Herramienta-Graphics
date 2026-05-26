from __future__ import annotations

from datetime import datetime, timezone
from typing import Annotated

from beanie import Document, Indexed, Replace, before_event
from pydantic import EmailStr, Field, field_validator


class User(Document):
    """
    Description:
        User document model persisted in MongoDB.

        Stores authentication identity fields, the hashed password and
        lifecycle timestamps.

    Args:
        None.

    Returns:
        User:
            Beanie document instance.
    """

    username: Annotated[str, Indexed(unique=True)]
    email: Annotated[EmailStr, Indexed(unique=True)]

    password_hash: str

    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    class Settings:
        """
        Description:
            Beanie configuration for the user collection.

        Args:
            None.

        Returns:
            Settings:
                Embedded Beanie settings class.
        """

        name = "users"

    @field_validator("username")
    @classmethod
    def normalize_username(cls, username_value: str) -> str:
        """
        Description:
            Normalize username before persistence.

        Args:
            username_value (str):
                Raw username value.

        Returns:
            str:
                Trimmed and lowercase username.
        """

        return username_value.strip().lower()

    @field_validator("email")
    @classmethod
    def normalize_email(cls, email_value: EmailStr) -> str:
        """
        Description:
            Normalize email before persistence.

        Args:
            email_value (EmailStr):
                Raw email value.

        Returns:
            str:
                Lowercase email.
        """

        return str(email_value).lower()

    @before_event(Replace)
    def update_timestamp(self) -> None:
        """
        Description:
            Refresh the `updated_at` field before replace operations.

        Args:
            self (User):
                Current user document.

        Returns:
            None:
                Mutates the current instance timestamp.
        """

        self.updated_at = datetime.now(timezone.utc)
