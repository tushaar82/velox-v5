"""
API endpoints for broker account management.
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel

from ...core.database import get_db
from ...core.security import get_current_user
from ...models.user import User, BrokerAccount, BrokerType, Balance
from ...services.broker_adapter.factory import BrokerAdapterFactory
from ...services.broker_adapter.base import BrokerException

router = APIRouter()


# Pydantic models
class BrokerAccountCreate(BaseModel):
    """Request model for creating a broker account."""
    broker_type: str
    account_name: str
    account_id: str
    api_key: Optional[str] = None
    api_secret: Optional[str] = None
    access_token: Optional[str] = None
    is_primary: bool = False


class BrokerAccountUpdate(BaseModel):
    """Request model for updating a broker account."""
    account_name: Optional[str] = None
    api_key: Optional[str] = None
    api_secret: Optional[str] = None
    access_token: Optional[str] = None
    is_active: Optional[bool] = None
    is_primary: Optional[bool] = None


class BrokerAccountResponse(BaseModel):
    """Response model for broker account."""
    id: int
    user_id: int
    broker_type: str
    account_name: str
    account_id: str
    is_active: bool
    is_primary: bool
    created_at: str
    updated_at: str

    class Config:
        from_attributes = True


class BalanceResponse(BaseModel):
    """Response model for balance."""
    id: int
    broker_account_id: int
    available_cash: float
    total_cash: float
    margin_used: float
    margin_available: float
    updated_at: str

    class Config:
        from_attributes = True


class BrokerConnectionTest(BaseModel):
    """Response model for broker connection test."""
    success: bool
    broker_name: str
    message: str


@router.get("/supported", response_model=List[str])
async def get_supported_brokers():
    """
    Get list of supported broker types.
    """
    return BrokerAdapterFactory.get_supported_brokers()


@router.get("", response_model=List[BrokerAccountResponse])
async def get_broker_accounts(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get all broker accounts for the current user.
    """
    result = await db.execute(
        select(BrokerAccount)
        .where(BrokerAccount.user_id == current_user.id)
        .order_by(BrokerAccount.is_primary.desc(), BrokerAccount.created_at.desc())
    )
    broker_accounts = result.scalars().all()

    return [
        BrokerAccountResponse(
            id=account.id,
            user_id=account.user_id,
            broker_type=account.broker_type.value,
            account_name=account.account_name,
            account_id=account.account_id,
            is_active=account.is_active,
            is_primary=account.is_primary,
            created_at=account.created_at.isoformat(),
            updated_at=account.updated_at.isoformat()
        )
        for account in broker_accounts
    ]


@router.get("/{broker_account_id}", response_model=BrokerAccountResponse)
async def get_broker_account(
    broker_account_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get a specific broker account.
    """
    result = await db.execute(
        select(BrokerAccount)
        .where(
            BrokerAccount.id == broker_account_id,
            BrokerAccount.user_id == current_user.id
        )
    )
    broker_account = result.scalar_one_or_none()

    if not broker_account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Broker account not found"
        )

    return BrokerAccountResponse(
        id=broker_account.id,
        user_id=broker_account.user_id,
        broker_type=broker_account.broker_type.value,
        account_name=broker_account.account_name,
        account_id=broker_account.account_id,
        is_active=broker_account.is_active,
        is_primary=broker_account.is_primary,
        created_at=broker_account.created_at.isoformat(),
        updated_at=broker_account.updated_at.isoformat()
    )


@router.post("", response_model=BrokerAccountResponse, status_code=status.HTTP_201_CREATED)
async def create_broker_account(
    data: BrokerAccountCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Create a new broker account.
    """
    # Validate broker type
    try:
        broker_type = BrokerType(data.broker_type.lower())
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid broker type: {data.broker_type}"
        )

    # Check if broker is supported
    if not BrokerAdapterFactory.is_broker_supported(broker_type):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Broker type {data.broker_type} is not supported"
        )

    # If setting as primary, unset other primary accounts
    if data.is_primary:
        await db.execute(
            select(BrokerAccount)
            .where(
                BrokerAccount.user_id == current_user.id,
                BrokerAccount.is_primary == True
            )
        )
        # Update existing primary accounts
        existing_primary = await db.execute(
            select(BrokerAccount)
            .where(
                BrokerAccount.user_id == current_user.id,
                BrokerAccount.is_primary == True
            )
        )
        for account in existing_primary.scalars():
            account.is_primary = False

    # Create broker account
    broker_account = BrokerAccount(
        user_id=current_user.id,
        broker_type=broker_type,
        account_name=data.account_name,
        account_id=data.account_id,
        api_key=data.api_key,
        api_secret=data.api_secret,
        access_token=data.access_token,
        is_primary=data.is_primary
    )

    db.add(broker_account)
    await db.commit()
    await db.refresh(broker_account)

    return BrokerAccountResponse(
        id=broker_account.id,
        user_id=broker_account.user_id,
        broker_type=broker_account.broker_type.value,
        account_name=broker_account.account_name,
        account_id=broker_account.account_id,
        is_active=broker_account.is_active,
        is_primary=broker_account.is_primary,
        created_at=broker_account.created_at.isoformat(),
        updated_at=broker_account.updated_at.isoformat()
    )


@router.patch("/{broker_account_id}", response_model=BrokerAccountResponse)
async def update_broker_account(
    broker_account_id: int,
    data: BrokerAccountUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Update a broker account.
    """
    result = await db.execute(
        select(BrokerAccount)
        .where(
            BrokerAccount.id == broker_account_id,
            BrokerAccount.user_id == current_user.id
        )
    )
    broker_account = result.scalar_one_or_none()

    if not broker_account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Broker account not found"
        )

    # Update fields
    if data.account_name is not None:
        broker_account.account_name = data.account_name
    if data.api_key is not None:
        broker_account.api_key = data.api_key
    if data.api_secret is not None:
        broker_account.api_secret = data.api_secret
    if data.access_token is not None:
        broker_account.access_token = data.access_token
    if data.is_active is not None:
        broker_account.is_active = data.is_active
    if data.is_primary is not None:
        # If setting as primary, unset other primary accounts
        if data.is_primary:
            existing_primary = await db.execute(
                select(BrokerAccount)
                .where(
                    BrokerAccount.user_id == current_user.id,
                    BrokerAccount.is_primary == True,
                    BrokerAccount.id != broker_account_id
                )
            )
            for account in existing_primary.scalars():
                account.is_primary = False
        broker_account.is_primary = data.is_primary

    await db.commit()
    await db.refresh(broker_account)

    return BrokerAccountResponse(
        id=broker_account.id,
        user_id=broker_account.user_id,
        broker_type=broker_account.broker_type.value,
        account_name=broker_account.account_name,
        account_id=broker_account.account_id,
        is_active=broker_account.is_active,
        is_primary=broker_account.is_primary,
        created_at=broker_account.created_at.isoformat(),
        updated_at=broker_account.updated_at.isoformat()
    )


@router.delete("/{broker_account_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_broker_account(
    broker_account_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Delete a broker account.
    """
    result = await db.execute(
        select(BrokerAccount)
        .where(
            BrokerAccount.id == broker_account_id,
            BrokerAccount.user_id == current_user.id
        )
    )
    broker_account = result.scalar_one_or_none()

    if not broker_account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Broker account not found"
        )

    await db.delete(broker_account)
    await db.commit()


@router.post("/{broker_account_id}/test-connection", response_model=BrokerConnectionTest)
async def test_broker_connection(
    broker_account_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Test connection to a broker account.
    """
    try:
        # Create broker adapter
        broker_adapter = await BrokerAdapterFactory.create_adapter_from_db(
            broker_account_id,
            db
        )

        # Test connection
        is_valid = await broker_adapter.validate_credentials()

        if is_valid:
            return BrokerConnectionTest(
                success=True,
                broker_name=broker_adapter.broker_name,
                message=f"Successfully connected to {broker_adapter.broker_name}"
            )
        else:
            return BrokerConnectionTest(
                success=False,
                broker_name=broker_adapter.broker_name,
                message=f"Failed to connect to {broker_adapter.broker_name}"
            )

    except BrokerException as e:
        return BrokerConnectionTest(
            success=False,
            broker_name=str(e.broker_name) if hasattr(e, 'broker_name') else "Unknown",
            message=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error testing connection: {str(e)}"
        )


@router.get("/{broker_account_id}/balance", response_model=BalanceResponse)
async def get_broker_balance(
    broker_account_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get balance for a broker account.
    """
    try:
        # Create broker adapter
        broker_adapter = await BrokerAdapterFactory.create_adapter_from_db(
            broker_account_id,
            db
        )

        # Connect and get balance
        await broker_adapter.connect()
        balance_info = await broker_adapter.get_balance()
        await broker_adapter.disconnect()

        # Update or create balance record
        result = await db.execute(
            select(Balance)
            .where(Balance.broker_account_id == broker_account_id)
        )
        balance = result.scalar_one_or_none()

        if balance:
            balance.available_cash = balance_info.available_cash
            balance.total_cash = balance_info.total_cash
            balance.margin_used = balance_info.margin_used
            balance.margin_available = balance_info.margin_available
        else:
            balance = Balance(
                broker_account_id=broker_account_id,
                available_cash=balance_info.available_cash,
                total_cash=balance_info.total_cash,
                margin_used=balance_info.margin_used,
                margin_available=balance_info.margin_available
            )
            db.add(balance)

        await db.commit()
        await db.refresh(balance)

        return BalanceResponse(
            id=balance.id,
            broker_account_id=balance.broker_account_id,
            available_cash=balance.available_cash,
            total_cash=balance.total_cash,
            margin_used=balance.margin_used,
            margin_available=balance.margin_available,
            updated_at=balance.updated_at.isoformat()
        )

    except BrokerException as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching balance: {str(e)}"
        )
