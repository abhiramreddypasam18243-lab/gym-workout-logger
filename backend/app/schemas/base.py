"""Base schema with strict extra field prohibition (spec SEC8, AC-09)."""

from pydantic import BaseModel, ConfigDict


class StrictSchema(BaseModel):
    """Schema that strictly forbids any unknown fields (AC-09).

    Any request containing unexpected fields (such as client-supplied user_id)
    will be rejected with 422 Unprocessable Entity.
    """

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )
