"""add image_urls to final_reports

Revision ID: 2026_02_09_0002
Revises: 2026_02_08_0001
Create Date: 2026-02-09

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "2026_02_09_0002"
down_revision = "2026_02_08_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("final_reports") as batch_op:
        batch_op.add_column(sa.Column("image_urls", sa.JSON(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("final_reports") as batch_op:
        batch_op.drop_column("image_urls")
