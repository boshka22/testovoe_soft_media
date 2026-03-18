"""Создание таблицы posts.

Revision ID: 0001
Create Date: 2024-01-01
"""

import sqlalchemy as sa
from alembic import op

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "posts",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("author", sa.String(100), nullable=False),
        sa.Column("views_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )
    op.create_index("ix_posts_created_at", "posts", ["created_at"])
    op.create_index("ix_posts_author", "posts", ["author"])

    # Триггер для автообновления updated_at при UPDATE
    op.execute(
        """
        CREATE OR REPLACE FUNCTION update_updated_at()
        RETURNS TRIGGER AS $$
        BEGIN
            NEW.updated_at = now();
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
    """
    )
    op.execute(
        """
        CREATE TRIGGER posts_updated_at
        BEFORE UPDATE ON posts
        FOR EACH ROW EXECUTE FUNCTION update_updated_at();
    """
    )


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS posts_updated_at ON posts;")
    op.execute("DROP FUNCTION IF EXISTS update_updated_at;")
    op.drop_index("ix_posts_author", table_name="posts")
    op.drop_index("ix_posts_created_at", table_name="posts")
    op.drop_table("posts")
