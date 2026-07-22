from fastapi import APIRouter, HTTPException
from app.database import execute_query, get_account_by_number
from app.logger import get_logger

logger = get_logger(__name__)
router = APIRouter()


@router.get("/accounts", tags=["Accounts"], summary="List all accounts")
async def list_accounts():
    """List all bank accounts — for testing."""
    accounts = execute_query(
        "SELECT account_number, account_holder, account_type, balance, currency, status FROM accounts ORDER BY id"
    )
    return {"accounts": accounts, "total": len(accounts)}


@router.get("/accounts/{account_number}", tags=["Accounts"], summary="Get account by number")
async def get_account(account_number: str):
    """Get account details by account number."""
    account = get_account_by_number(account_number)
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
    return {"account": account}


@router.get("/accounts/{account_number}/transactions", tags=["Accounts"], summary="Get transactions")
async def get_transactions(account_number: str, limit: int = 10):
    """Get transactions for an account."""
    account = get_account_by_number(account_number)
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")

    from app.database import get_transactions as db_get_transactions
    transactions = db_get_transactions(account["id"], limit=limit)
    return {
        "account_number": account_number,
        "transactions": transactions,
        "total": len(transactions)
    }
