"""
Broker adapter factory for creating broker-specific adapters.
"""
import logging
from typing import Dict, Type, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from .base import BrokerAdapter, BrokerException
from .nse_adapter import NSEAdapter
from .zerodha_adapter import ZerodhaAdapter
from ...models.user import BrokerAccount, BrokerType

logger = logging.getLogger(__name__)


class BrokerAdapterFactory:
    """Factory for creating broker adapters."""

    # Registry of broker adapters
    _adapters: Dict[BrokerType, Type[BrokerAdapter]] = {
        BrokerType.NSE: NSEAdapter,
        BrokerType.ZERODHA: ZerodhaAdapter,
        # Add more brokers as they are implemented
        # BrokerType.UPSTOX: UpstoxAdapter,
        # BrokerType.ANGEL_ONE: AngelOneAdapter,
        # BrokerType.ICICI_DIRECT: ICICIDirectAdapter,
    }

    @classmethod
    def register_adapter(cls, broker_type: BrokerType, adapter_class: Type[BrokerAdapter]):
        """
        Register a new broker adapter.

        Args:
            broker_type: Broker type enum value
            adapter_class: Adapter class to register
        """
        cls._adapters[broker_type] = adapter_class
        logger.info(f"Registered broker adapter: {broker_type.value} -> {adapter_class.__name__}")

    @classmethod
    def create_adapter(
        cls,
        broker_type: BrokerType,
        account_id: str,
        credentials: Dict[str, str]
    ) -> BrokerAdapter:
        """
        Create a broker adapter instance.

        Args:
            broker_type: Type of broker
            account_id: Broker account identifier
            credentials: Broker API credentials

        Returns:
            BrokerAdapter instance

        Raises:
            BrokerException: If broker type is not supported
        """
        adapter_class = cls._adapters.get(broker_type)

        if not adapter_class:
            supported = ", ".join([bt.value for bt in cls._adapters.keys()])
            raise BrokerException(
                f"Unsupported broker type: {broker_type.value}. Supported: {supported}",
                "Factory"
            )

        logger.info(f"Creating {broker_type.value} adapter for account {account_id}")
        return adapter_class(account_id, credentials)

    @classmethod
    async def create_adapter_from_db(
        cls,
        broker_account_id: int,
        db: AsyncSession
    ) -> BrokerAdapter:
        """
        Create a broker adapter from database broker account.

        Args:
            broker_account_id: Database ID of broker account
            db: Database session

        Returns:
            BrokerAdapter instance

        Raises:
            BrokerException: If broker account not found or invalid
        """
        # Fetch broker account from database
        result = await db.execute(
            select(BrokerAccount).where(
                BrokerAccount.id == broker_account_id,
                BrokerAccount.is_active == True
            )
        )
        broker_account = result.scalar_one_or_none()

        if not broker_account:
            raise BrokerException(
                f"Broker account {broker_account_id} not found or inactive",
                "Factory"
            )

        # Build credentials dictionary
        credentials = {}
        if broker_account.api_key:
            credentials["api_key"] = broker_account.api_key
        if broker_account.api_secret:
            credentials["api_secret"] = broker_account.api_secret
        if broker_account.access_token:
            credentials["access_token"] = broker_account.access_token

        # Create adapter
        return cls.create_adapter(
            broker_type=broker_account.broker_type,
            account_id=broker_account.account_id,
            credentials=credentials
        )

    @classmethod
    async def create_adapter_for_user(
        cls,
        user_id: int,
        db: AsyncSession,
        broker_type: Optional[BrokerType] = None
    ) -> BrokerAdapter:
        """
        Create a broker adapter for a user.

        If broker_type is specified, uses that specific broker.
        Otherwise, uses the user's primary broker account.

        Args:
            user_id: User ID
            db: Database session
            broker_type: Specific broker type (optional)

        Returns:
            BrokerAdapter instance

        Raises:
            BrokerException: If no broker account found
        """
        # Build query
        query = select(BrokerAccount).where(
            BrokerAccount.user_id == user_id,
            BrokerAccount.is_active == True
        )

        if broker_type:
            query = query.where(BrokerAccount.broker_type == broker_type)
        else:
            query = query.where(BrokerAccount.is_primary == True)

        # Execute query
        result = await db.execute(query)
        broker_account = result.scalar_one_or_none()

        if not broker_account:
            broker_filter = f" with type {broker_type.value}" if broker_type else " (primary)"
            raise BrokerException(
                f"No active broker account found for user {user_id}{broker_filter}",
                "Factory"
            )

        # Create adapter from broker account
        return await cls.create_adapter_from_db(broker_account.id, db)

    @classmethod
    def get_supported_brokers(cls) -> list[str]:
        """
        Get list of supported broker types.

        Returns:
            List of broker type names
        """
        return [bt.value for bt in cls._adapters.keys()]

    @classmethod
    def is_broker_supported(cls, broker_type: BrokerType) -> bool:
        """
        Check if a broker type is supported.

        Args:
            broker_type: Broker type to check

        Returns:
            True if supported, False otherwise
        """
        return broker_type in cls._adapters
