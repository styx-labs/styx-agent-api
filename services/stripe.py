import stripe
from dotenv import load_dotenv
import os

load_dotenv()

stripe.api_key = os.getenv("STRIPE_API_KEY")

# First create products for each tier
basic_product = stripe.Product.create(
    name="Basic Plan",
    description="100 credits - Perfect for small teams or individual recruiters getting started with AI-powered recruiting.",
)

growth_product = stripe.Product.create(
    name="Growth Plan",
    description="500 credits - Ideal for growing teams who need advanced features and higher volume candidate processing.",
)

# Create prices for the products
basic_price = stripe.Price.create(
    product=basic_product.id,
    unit_amount=999,  # $9.99 in cents
    currency="usd",
    metadata={"credits": "100", "cost_per_search": "0.10"},
)

growth_price = stripe.Price.create(
    product=growth_product.id,
    unit_amount=4499,  # $44.99 in cents
    currency="usd",
    metadata={"credits": "500", "cost_per_search": "0.09"},
)

PRICE_IDS = {
    "basic": basic_price.id,
    "growth": growth_price.id,
}


def create_checkout_session(plan_id: str, user_id: str):
    """Create a Stripe checkout session for the specified plan"""
    try:
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
            mode="payment",
            success_url=(
                "http://localhost:3000"
                if os.getenv("DEVELOPMENT_MODE") == "true"
                else "https://www.styxlabs.co"
            )
            + "/pricing/success",
            cancel_url=(
                "http://localhost:3000"
                if os.getenv("DEVELOPMENT_MODE") == "true"
                else "https://www.styxlabs.co"
            )
            + "/pricing/cancel",
            metadata={
                "user_id": user_id,
                "plan_id": plan_id,
            },
        )
        return checkout_session.url

    except stripe.error.StripeError as e:
        raise Exception(f"Stripe error: {str(e)}")
    except Exception as e:
        raise Exception(f"Error creating checkout session: {str(e)}")
