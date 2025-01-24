from collections import defaultdict
from typing import Optional
from fastapi import Depends, APIRouter, HTTPException, Request, Header, status, Query
import stripe
import logging
from open_webui.models.users import UserModel, Users
from open_webui.utils.auth import get_current_user

from sqlalchemy import create_engine
from sqlalchemy.sql import text
from sqlalchemy.orm import sessionmaker
from datetime import datetime, date, timedelta


from open_webui.utils.stripe import get_user_max_budget, update_user_max_budget, get_subscription_info, hash_token

from open_webui.env import (
    STRIPE_WEBHOOK_SECRET,
    STRIPE_SECRET_KEY
)
from pydantic import BaseModel
from open_webui.env import DATABASE_URL, SRC_LOG_LEVELS

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["STRIPE"])

stripe.api_key = STRIPE_SECRET_KEY

router = APIRouter()


# Create engine and session
engine = create_engine(DATABASE_URL)
Session = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class TotalSpending(BaseModel):
    total_spend: float
    total_input_tokens: int
    total_output_tokens: int

class DailyTotalSpending(TotalSpending):
    day: date
    
class SpendingPerModel:
    model: str
    daily_spending: list[DailyTotalSpending]
    

def get_db():
    db = Session()
    try:
        yield db
    finally:
        db.close()

@router.get("/spendings")
async def global_spend_per_user(
     start_date: Optional[str] = Query(
        default='2024-12-18',
        description="Time from which to start viewing spend",
    ),
    end_date: Optional[str] = Query(
        default='2024-12-20',
        description="Time till which to view spend",
    ),
    per_day: Optional[str]=Query(
        default=False,
        description="If `True`, the model_cost, total_input_tokens, total_output_tokens are computed per model, per day given the time frame. Else, it's aggragated per model",
    ),
    user: UserModel=Depends(get_current_user), 
    db_session: Session=Depends(get_db)
):
    if start_date is None or end_date is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": "Please provide start_date and end_date"},
        )
    
    api_key = hash_token(user.llm_api_key)

    # Start from beginning of start_date
    start_date = datetime.strptime(start_date, "%Y-%m-%d")
    # End at the end of end_date
    end_date = datetime.strptime(end_date, "%Y-%m-%d") + timedelta(days=1) - timedelta(seconds=1)

    query_text = """
    SELECT 
        DATE("startTime") as day,
        model,
        SUM(spend) as total_spend,
        SUM(prompt_tokens) as total_input_tokens,
        SUM(completion_tokens) as total_output_tokens
    FROM "LiteLLM_SpendLogs"
    WHERE 
        "startTime" BETWEEN :start_date AND :end_date
        AND api_key = :api_key
    GROUP BY DATE("startTime"), model
    ORDER BY model, day DESC;
    """
    result = db_session.execute(
        text(query_text).bindparams(
            start_date=start_date,
            end_date=end_date,
            api_key=api_key
        )
    )

    # Group results by model
    model_spending = defaultdict(list)
    for row in result.fetchall():
        model_name = row.model
        daily_spend = DailyTotalSpending(
            day=row.day,
            total_spend=row.total_spend,
            total_input_tokens=row.total_input_tokens,
            total_output_tokens=row.total_output_tokens
        )
        model_spending[model_name].append(daily_spend)

    log.info(f"Result: {model_spending}")

    if per_day:
        daily_spending_per_model = [
            {'model':model, 'daily_spending':spending}
            for model, spending in model_spending.items()
        ]
        return daily_spending_per_model
    else:
        aggregated_spending = []
        for model_name, daily_spendings in model_spending.items():
            aggregated_spending.append(
                {
                    'model': model_name,
                    'total_spend': sum(spend.total_spend for spend in daily_spendings),
                    'total_input_tokens': sum(spend.total_input_tokens for spend in daily_spendings),
                    'total_output_tokens': sum(spend.total_output_tokens for spend in daily_spendings)
                }
            )
        
        return aggregated_spending


@router.get("/subscription_info")
async def get_subs_info(user: UserModel=Depends(get_current_user)):
    spend, max_budget, budget_duration = await get_subscription_info(key=user.llm_api_key)
    return {
        "spend": spend,
        "max_budget": max_budget,
        'budget_duration': budget_duration,
        'type_subscription': "Subscription" if max_budget is None else "One-Time Payment"
    }


@router.post("/webhook")
async def stripe_webhook(request: Request, stripe_signature: str = Header(None)):
    """
    Handles incoming Stripe webhook events.
    """
    try:
        # Retrieve the raw body and Stripe signature from the request
        payload = await request.body()
        sig_header = stripe_signature

        # Verify the event by using the Stripe SDK
        event = stripe.Webhook.construct_event(
            payload, sig_header, STRIPE_WEBHOOK_SECRET
        )
        log.info(f" Received Event: {event['type']}")
        event_type = event["type"]
        event_data = event["data"]["object"]
        log.info(f"payment_intent: {event_data}")
        
        # Handle the event (depending on its type)
        if event_type == "checkout.session.completed":

            customer_email = event_data['customer_email']
            user = Users.get_user_by_email(customer_email)
            key = user.llm_api_key
            log.info(f"api_key: {key}") 

            mode = event_data["mode"]
            amount = event_data['amount_total'] / 100 

            if mode == 'payment':
                log.info(f"Payment: Payment for {amount} succeeded!")
                current_budget = get_user_max_budget(key)
                log.info(f"CURRENT BUDGET: {current_budget}")
                new_budget = current_budget + amount
                update_user_max_budget(key, max_budget=new_budget, spend=0)
            
            if mode == 'subscription':
                pass

        elif event_type == "invoice.payment_succeeded": # subs
            customer_email = event_data['customer_email']
            user = Users.get_user_by_email(customer_email)
            key = user.llm_api_key
            log.info(f"api_key: {key}") 

            amount = event_data['amount_paid'] / 100
            plan = event_data['lines']['data'][0]['plan']
            interval = plan['interval'] # days, months, year, etc
            interval_count = plan['interval_count']
            log.info(f"Subscription: Payment for {amount} succeeded!")

            update_user_max_budget(
                key, spend=0, 
                max_budget=None,
                budget_duration=f"{interval_count}{interval[0]}"
            )
        else:
            log.error(f"Unhandled event type: {event['type']}")

        return {"status": "success"}
    
    except stripe.error.SignatureVerificationError as e:
        # Invalid signature
        print("Webhook signature verification failed.")
        raise HTTPException(status_code=400, detail="Invalid signature")
    except Exception as e:
        # Other errors
        print(f"Error while handling webhook: {str(e)}")
        raise HTTPException(status_code=400, detail=f"Webhook error {str(e)}")


@router.get("/test")
async def test_endpoint():
    return {"message": "Hello"}