from pydantic import BaseModel, Field, ConfigDict


class ConfirmPasswordInboundSchema(BaseModel):
    # min length of 1 prevents the client from sending an empty string.
    password: str = Field(
        ...,
        min_length = 1,
        description = "The user's password for re-authentication."
    )

    # Prevent client from adding extra fields.
    model_config = ConfigDict(extra = "forbid")
