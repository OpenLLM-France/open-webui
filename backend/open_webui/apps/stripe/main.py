from fastapi import Depends, FastAPI, HTTPException, Request, Header, status
from fastapi import responses
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, RedirectResponse, StreamingResponse
import stripe
import logging
import requests
from open_webui.apps.webui.models.users import UserModel, Users
from open_webui.utils.utils import get_current_user, get_http_authorization_cred

from .utils import get_user_max_budget, update_user_max_budget, get_subscription_info

from open_webui.config import (
    CORS_ALLOW_ORIGIN,
    STRIPE_WEBHOOK_SECRET,
    STRIPE_SECRET_KEY
)

from open_webui.constants import ERROR_MESSAGES
from open_webui.env import ENV, SRC_LOG_LEVELS, WEBUI_URL

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["STRIPE"])

stripe.api_key = STRIPE_SECRET_KEY

app = FastAPI(
    docs_url="/docs" if ENV == "dev" else None,
    openapi_url="/openapi.json" if ENV == "dev" else None,
    redoc_url=None,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ALLOW_ORIGIN,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/subscription_info")
async def get_subs_info(user: UserModel=Depends(get_current_user)):
    spend, max_budget, budget_duration = await get_subscription_info(key=user.llm_api_key)
    return {
        "spend": spend,
        "max_budget": max_budget,
        'budget_duration': budget_duration,
        'type_subscription': "Subscription" if max_budget is None else "One-Time Payment"
    }


@app.post("/webhook")
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


@app.get("/test")
async def test_endpoint():
    return {"message": "Hello"}