"""Initial schema: users, campaigns, maps, layers, objects, exports

Revision ID: 0001
Revises:
Create Date: 2026-05-10

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute('CREATE EXTENSION IF NOT EXISTS "pgcrypto"')

    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("display_name", sa.String(120), nullable=False),
        sa.Column("avatar_url", sa.String(2048)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )

    op.create_table(
        "oauth_identities",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("provider", sa.String(32), nullable=False),
        sa.Column("provider_user_id", sa.String(256), nullable=False),
        sa.Column("access_token", sa.Text),
        sa.Column("refresh_token", sa.Text),
        sa.Column("token_expires_at", sa.DateTime(timezone=True)),
        sa.Column("raw_profile", postgresql.JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.UniqueConstraint("provider", "provider_user_id", name="uq_oauth_identities_provider_provider_user_id"),
    )
    op.create_index("ix_oauth_identities_user_id", "oauth_identities", ["user_id"])

    op.create_table(
        "campaigns",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("owner_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("description", sa.String(1000)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_campaigns_owner_id", "campaigns", ["owner_id"])

    op.create_table(
        "campaign_members",
        sa.Column("campaign_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("campaigns.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("role", sa.Enum("owner", "dm", "player", "viewer", name="campaignrole"), nullable=False),
        sa.Column("joined_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )

    op.create_table(
        "campaign_invites",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("campaign_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("campaigns.id", ondelete="CASCADE"), nullable=False),
        sa.Column("created_by_user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("code", sa.String(64), unique=True, nullable=False),
        sa.Column("role", sa.Enum("owner", "dm", "player", "viewer", name="campaignrole"), nullable=False, server_default="player"),
        sa.Column("max_uses", sa.Integer),
        sa.Column("use_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("expires_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_campaign_invites_campaign_id", "campaign_invites", ["campaign_id"])
    op.create_index("ix_campaign_invites_code", "campaign_invites", ["code"])

    op.create_table(
        "campaign_maps",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("campaign_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("campaigns.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("width", sa.Integer, nullable=False, server_default="1920"),
        sa.Column("height", sa.Integer, nullable=False, server_default="1080"),
        sa.Column("grid_size", sa.Integer, nullable=False, server_default="70"),
        sa.Column("background_color", sa.String(32), nullable=False, server_default="'#1f2937'"),
        sa.Column("image_object_key", sa.String(1024)),
        sa.Column("image_url", sa.String(2048)),
        sa.Column("image_name", sa.String(255)),
        sa.Column("image_content_type", sa.String(120)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_campaign_maps_campaign_id", "campaign_maps", ["campaign_id"])

    op.create_table(
        "map_layers",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("map_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("campaign_maps.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("kind", sa.String(32), nullable=False),
        sa.Column("visible", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("audience", sa.String(16), nullable=False, server_default="'all'"),
        sa.Column("opacity", sa.Float, nullable=False, server_default="1.0"),
        sa.Column("sort_order", sa.Integer, nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_map_layers_map_id", "map_layers", ["map_id"])

    op.create_table(
        "map_objects",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("map_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("campaign_maps.id", ondelete="CASCADE"), nullable=False),
        sa.Column("layer_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("map_layers.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(120), nullable=False, server_default="''"),
        sa.Column("kind", sa.String(32), nullable=False),
        sa.Column("x", sa.Float, nullable=False, server_default="0"),
        sa.Column("y", sa.Float, nullable=False, server_default="0"),
        sa.Column("width", sa.Float, nullable=False, server_default="1"),
        sa.Column("height", sa.Float, nullable=False, server_default="1"),
        sa.Column("rotation", sa.Float, nullable=False, server_default="0"),
        sa.Column("visible", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("audience", sa.String(16), nullable=False, server_default="'all'"),
        sa.Column("geometry", postgresql.JSONB),
        sa.Column("style", postgresql.JSONB),
        sa.Column("properties", postgresql.JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_map_objects_map_id", "map_objects", ["map_id"])
    op.create_index("ix_map_objects_layer_id", "map_objects", ["layer_id"])

    op.create_table(
        "map_exports",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("map_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("campaign_maps.id", ondelete="CASCADE"), nullable=False),
        sa.Column("format", sa.String(16), nullable=False),
        sa.Column("include_hidden_layers", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("options", postgresql.JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("status", sa.String(16), nullable=False, server_default="'queued'"),
        sa.Column("error", sa.Text),
        sa.Column("download_url", sa.String(2048)),
        sa.Column("requested_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
    )
    op.create_index("ix_map_exports_map_id", "map_exports", ["map_id"])


def downgrade() -> None:
    op.drop_table("map_exports")
    op.drop_table("map_objects")
    op.drop_table("map_layers")
    op.drop_table("campaign_maps")
    op.drop_table("campaign_invites")
    op.drop_table("campaign_members")
    op.drop_table("campaigns")
    op.drop_table("oauth_identities")
    op.drop_table("users")
    op.execute("DROP TYPE IF EXISTS campaignrole")
    op.execute('DROP EXTENSION IF EXISTS "pgcrypto"')
