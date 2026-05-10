"""CLI entry point for database management.

Usage:
    dndmap-db migrate     -- run alembic upgrade head
    dndmap-db seed        -- insert dev fixtures
    dndmap-db reset       -- drop all tables, re-migrate, seed
"""
import asyncio
import os
import sys

from alembic import command
from alembic.config import Config


def _alembic_cfg() -> Config:
    here = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    cfg = Config(os.path.join(here, "alembic.ini"))
    db_url = os.environ.get("DATABASE_URL")
    if db_url:
        if db_url.startswith("postgres://"):
            db_url = db_url.replace("postgres://", "postgresql+asyncpg://", 1)
        elif db_url.startswith("postgresql://") and "+asyncpg" not in db_url:
            db_url = db_url.replace("postgresql://", "postgresql+asyncpg://", 1)
        cfg.set_main_option("sqlalchemy.url", db_url)
    return cfg


async def _seed() -> None:
    from app.db.engine import make_engine, make_session_factory
    from app.db import models as orm

    db_url = os.environ.get("DATABASE_URL", "postgresql+asyncpg://postgres:postgres@localhost:5432/dndmap")
    if db_url.startswith("postgres://"):
        db_url = db_url.replace("postgres://", "postgresql+asyncpg://", 1)
    elif db_url.startswith("postgresql://") and "+asyncpg" not in db_url:
        db_url = db_url.replace("postgresql://", "postgresql+asyncpg://", 1)

    engine = make_engine(db_url)
    factory = make_session_factory(engine)

    async with factory() as session:
        user = orm.User(display_name="Dev DM", avatar_url=None)
        session.add(user)
        await session.flush()

        campaign = orm.Campaign(owner_id=user.id, name="Dev Campaign", description="Seeded for development")
        session.add(campaign)
        await session.flush()

        member = orm.CampaignMember(campaign_id=campaign.id, user_id=user.id, role=orm.CampaignRole.OWNER)
        session.add(member)
        await session.flush()

        campaign_map = orm.CampaignMap(
            campaign_id=campaign.id,
            name="Starter Map",
            width=1920,
            height=1080,
        )
        session.add(campaign_map)
        await session.flush()

        layer = orm.MapLayer(
            map_id=campaign_map.id,
            name="Objects",
            kind="objects",
        )
        session.add(layer)
        await session.commit()

    await engine.dispose()
    print("Seeded: 1 user, 1 campaign, 1 map, 1 layer")


async def _reset() -> None:
    from app.db.engine import make_engine
    from app.db.base import Base
    import app.db.models  # noqa: F401

    db_url = os.environ.get("DATABASE_URL", "postgresql+asyncpg://postgres:postgres@localhost:5432/dndmap")
    if db_url.startswith("postgres://"):
        db_url = db_url.replace("postgres://", "postgresql+asyncpg://", 1)
    elif db_url.startswith("postgresql://") and "+asyncpg" not in db_url:
        db_url = db_url.replace("postgresql://", "postgresql+asyncpg://", 1)

    engine = make_engine(db_url)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()
    print("Dropped all tables")


def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: dndmap-db [migrate|seed|reset]")
        sys.exit(1)

    cmd = sys.argv[1]

    if cmd == "migrate":
        cfg = _alembic_cfg()
        command.upgrade(cfg, "head")
        print("Migrations complete")
    elif cmd == "seed":
        asyncio.run(_seed())
    elif cmd == "reset":
        asyncio.run(_reset())
        cfg = _alembic_cfg()
        command.upgrade(cfg, "head")
        print("Migrations complete after reset")
        asyncio.run(_seed())
    else:
        print(f"Unknown command: {cmd}")
        sys.exit(1)


if __name__ == "__main__":
    main()
