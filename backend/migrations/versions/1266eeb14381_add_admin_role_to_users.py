"""add admin role to users

Revision ID: 1266eeb14381
Revises: 2178feed7759
Create Date: 2026-09-16 19:16:46.283994

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "1266eeb14381"

down_revision: Union[
    str,
    Sequence[str],
    None,
] = "2178feed7759"

branch_labels: Union[
    str,
    Sequence[str],
    None,
] = None

depends_on: Union[
    str,
    Sequence[str],
    None,
] = None


def upgrade() -> None:
    """Add administrator role to users."""

    with op.batch_alter_table(
        "users",
        schema=None,
    ) as batch_op:

        batch_op.add_column(
            sa.Column(
                "is_admin",
                sa.Boolean(),
                nullable=False,
                server_default=sa.false(),
            )
        )


def downgrade() -> None:
    """Remove administrator role from users."""

    with op.batch_alter_table(
        "users",
        schema=None,
    ) as batch_op:

        batch_op.drop_column(
            "is_admin"
        )