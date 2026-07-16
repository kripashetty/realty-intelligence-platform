"""Initial schema: import_batches, listings, pricing_recommendations

Revision ID: 001
Revises:
Create Date: 2026-07-14
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "import_batches",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("uploaded_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("total_rows", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("imported_rows", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("skipped_rows", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("skip_reasons", postgresql.JSONB(), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="processing"),
        sa.Column(
            "geocoding_status", sa.String(20), nullable=False, server_default="pending"
        ),
    )
    op.create_index("ix_import_batches_uploaded_at", "import_batches", ["uploaded_at"])

    op.create_table(
        "listings",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("import_batch_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("title", sa.Text(), nullable=True),
        sa.Column("address", sa.Text(), nullable=False),
        sa.Column("latitude", sa.Float(), nullable=True),
        sa.Column("longitude", sa.Float(), nullable=True),
        sa.Column("price_eur", sa.Numeric(10, 2), nullable=False),
        sa.Column("size_m2", sa.Numeric(7, 2), nullable=False),
        sa.Column("rooms", sa.Numeric(4, 1), nullable=False),
        sa.Column("floor", sa.SmallInteger(), nullable=True),
        sa.Column("platform", sa.String(100), nullable=False),
        sa.Column("source_url", sa.Text(), nullable=False),
        sa.Column("listing_date", sa.Date(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["import_batch_id"], ["import_batches.id"]),
        sa.UniqueConstraint(
            "source_url", "listing_date", name="uq_listing_source_url_date"
        ),
    )
    op.create_index("ix_listing_lat_lng", "listings", ["latitude", "longitude"])
    op.create_index("ix_listing_price_eur", "listings", ["price_eur"])
    op.create_index("ix_listing_size_rooms", "listings", ["size_m2", "rooms"])
    op.create_index("ix_listing_date", "listings", ["listing_date"])
    op.create_index("ix_listing_batch_id", "listings", ["import_batch_id"])

    op.create_table(
        "pricing_recommendations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("generated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("import_batch_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("apt_address", sa.Text(), nullable=False),
        sa.Column("apt_latitude", sa.Float(), nullable=True),
        sa.Column("apt_longitude", sa.Float(), nullable=True),
        sa.Column("apt_size_m2", sa.Numeric(7, 2), nullable=False),
        sa.Column("apt_rooms", sa.Numeric(4, 1), nullable=False),
        sa.Column("apt_floor", sa.SmallInteger(), nullable=True),
        sa.Column("apt_amenities", postgresql.JSONB(), nullable=True),
        sa.Column("comparable_count", sa.Integer(), nullable=False),
        sa.Column("recommended_price_eur", sa.Numeric(10, 2), nullable=False),
        sa.Column("confidence_low_eur", sa.Numeric(10, 2), nullable=False),
        sa.Column("confidence_high_eur", sa.Numeric(10, 2), nullable=False),
        sa.Column("percentile_rank", sa.Float(), nullable=False),
        sa.Column("explanation", sa.Text(), nullable=True),
        sa.Column("factors", postgresql.JSONB(), nullable=False),
        sa.Column("comparable_listing_ids", postgresql.JSONB(), nullable=False),
        sa.Column("confidence_level", sa.String(10), nullable=False),
        sa.ForeignKeyConstraint(["import_batch_id"], ["import_batches.id"]),
    )
    op.create_index(
        "ix_pricing_recommendations_generated_at",
        "pricing_recommendations",
        ["generated_at"],
    )


def downgrade() -> None:
    op.drop_table("pricing_recommendations")
    op.drop_table("listings")
    op.drop_table("import_batches")
