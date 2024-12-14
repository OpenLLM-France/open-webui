from fastapi import Depends, FastAPI, HTTPException, Request, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
import stripe
import logging
import requests
from open_webui.apps.webui.models.users import UserModel
from open_webui.utils.utils import get_current_user, get_http_authorization_cred

from .utils import get_user_max_budget, update_user_max_budget

from open_webui.config import (
    CORS_ALLOW_ORIGIN,
    STRIPE_WEBHOOK_SECRET,
    STRIPE_SECRET_KEY
)

from open_webui.constants import ERROR_MESSAGES
from open_webui.env import ENV, SRC_LOG_LEVELS

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

        user = get_current_user(request, get_http_authorization_cred(request.headers.get("Authorization")))

        # Handle the event (depending on its type)
        if event["type"] == "payment_intent.succeeded":
            payment_intent = event["data"]["object"]
            print(f"Payment for {payment_intent['amount']} succeeded!")
            # Perform actions like updating a database, sending an email, etc.
            # Add budget to litellm
            user_key = user.llm_api_key
            current_budget = get_user_max_budget(user_key)
            print("CURRENT BUDGET: ", current_budget)
            new_budget = current_budget + payment_intent["amount"]/100
            update_user_max_budget(user_key, new_budget)

        elif event["type"] == "invoice.payment_failed":
            invoice = event["data"]["object"]
            print(f"Payment for Invoice {invoice['id']} failed.")
            # Handle failed payments

        else:
            print(f"Unhandled event type: {event['type']}")

        # Return a 200 response to acknowledge receipt of the event
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