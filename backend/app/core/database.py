"""
app/core/database.py

MongoDB connection manager for EduSync ERP.
Uses Motor (async MongoDB driver) with a singleton client pattern.
"""

import logging
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from app.core.config import settings

logger = logging.getLogger(__name__)


class DatabaseManager:
    """
    Manages the lifecycle of the MongoDB connection.
    Uses the singleton pattern so only one connection
    is created and reused throughout the application.
    """

    client: AsyncIOMotorClient | None = None
    database: AsyncIOMotorDatabase | None = None


# Module-level singleton instance
db_manager = DatabaseManager()


async def connect_to_mongo() -> None:
    """
    Opens the MongoDB connection when the FastAPI app starts.
    Performs a server ping to verify the connection is live.
    Raises an exception if the database is unreachable.
    """
    logger.info("Connecting to MongoDB...")

    try:
        db_manager.client = AsyncIOMotorClient(
            settings.MONGODB_URI,
            serverSelectionTimeoutMS=5000,  # 5-second timeout for server selection
        )

        # Ping the server to confirm the connection is alive
        await db_manager.client.admin.command("ping")

        db_manager.database = db_manager.client[settings.DATABASE_NAME]

        logger.info(
            f"Successfully connected to MongoDB | Database: '{settings.DATABASE_NAME}'"
        )

    except Exception as e:
        logger.error(f"Failed to connect to MongoDB: {e}")
        # Re-raise so the lifespan handler can decide how to respond
        raise


async def close_mongo_connection() -> None:
    """
    Closes the MongoDB connection when the FastAPI app shuts down.
    Safely handles the case where the client was never initialized.
    """
    if db_manager.client is not None:
        db_manager.client.close()
        db_manager.client = None
        db_manager.database = None
        logger.info("MongoDB connection closed.")
    else:
        logger.warning("MongoDB client was not initialized; nothing to close.")


def get_database() -> AsyncIOMotorDatabase:
    """
    Returns the active database instance.
    Call this function inside route handlers via FastAPI Depends()
    or directly in service functions.

    Raises:
        RuntimeError: If the database connection has not been established.
    """
    if db_manager.database is None:
        raise RuntimeError(
            "Database is not connected. "
            "Ensure connect_to_mongo() was called during application startup."
        )
    return db_manager.database
