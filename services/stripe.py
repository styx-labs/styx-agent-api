import stripe
from services.get_secret import get_secret
import os
from dotenv import load_dotenv
import services.firestore as firestore
from services.firestore import add_search_credits, update_user_subscription
import logging

load_dotenv()

stripe.api_key = get_secret("stripe-api-key", "1")

# Create products for paid tiers only
growth_product = stripe.Product.create(
    name="Growth",
    description="Best for small teams and agencies - 1000 credits with rollover credits (2 months), unlimited jobs, and dedicated support.",
)

pro_product = stripe.Product.create(
    name="Pro",
    description="Best for large teams - 5000 credits with dedicated Slack channel and ATS integrations.",
)

# Create prices for the paid products
growth_price = stripe.Price.create(
    product=growth_product.id,
    unit_amount=20000,  # $200.00 in cents
    currency="usd",
    recurring={"interval": "month"},
    metadata={"credits": "1000"},
)

pro_price = stripe.Price.create(
    product=pro_product.id,
    unit_amount=75000,  # $750.00 in cents
    currency="usd",
    recurring={"interval": "month"},
    metadata={"credits": "5000"},
)

PRICE_IDS = {
    "growth": growth_price.id,
    "pro": pro_price.id,
}


def create_checkout_session(plan_id: str, user_id: str):
    """Create a Stripe checkout session for the specified plan"""
    try:
        # Handle free tier
        if plan_id.lower() == "starter":
            # Add free credits and update subscription status
            add_search_credits(user_id, 50)
            update_user_subscription(user_id, None, "free_tier")
            return (
                "http://localhost:3000"
                if os.getenv("DEVELOPMENT_MODE") == "true"
                else "https://app.styxlabs.co"
            ) + "/pricing/success"

        price_id = PRICE_IDS.get(plan_id.lower())
        if not price_id:
            raise ValueError(f"Invalid plan ID: {plan_id}")

        checkout_session = stripe.checkout.Session.create(
            client_reference_id=user_id,
            line_items=[
                {
                    "price": price_id,
                    "quantity": 1,
                }
            ],
            mode="subscription",
            subscription_data={
                "metadata": {
                    "user_id": user_id,
                    "plan_id": plan_id,
                }
            },
            success_url=(
                "http://localhost:3000"
                if os.getenv("DEVELOPMENT_MODE") == "true"
                else "https://app.styxlabs.co"
            )
            + "/pricing/success",
            cancel_url=(
                "http://localhost:3000"
                if os.getenv("DEVELOPMENT_MODE") == "true"
                else "https://app.styxlabs.co"
            )
            + "/pricing/cancel",
        )
        return checkout_session.url

    except stripe.error.StripeError as e:
        raise Exception(f"Stripe error: {str(e)}")
    except Exception as e:
        raise Exception(f"Error creating checkout session: {str(e)}")


def add_monthly_credits_to_free_users():
    """Add monthly credits to all free tier users"""
    try:
        # Get all users with free_tier status from Firestore
        users = firestore.get_free_tier_users()
        for user_id in users:
            add_search_credits(user_id, 50)
        return True
    except Exception as e:
        logging.error(f"Error adding monthly credits to free users: {str(e)}")
        return False
