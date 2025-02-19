import stripe
from fastapi import HTTPException, status
import logging
from services.get_secret import get_secret
import services.firestore as firestore

CREDITS_BY_PLAN = {
    "starter": 50,
    "growth": 1000,
    "pro": 5000,
}


async def handle_stripe_webhook(payload_str: str, sig_header: str):
    """Handle incoming Stripe webhook events"""
    try:
        if not sig_header:
            raise HTTPException(status_code=400, detail="No signature header")

        try:
            event = stripe.Webhook.construct_event(
                payload_str, sig_header, get_secret("stripe-webhook-secret", "1")
            )

        except ValueError as e:
            raise HTTPException(status_code=400, detail=f"Invalid payload: {str(e)}")
        except stripe.error.SignatureVerificationError as e:
            raise HTTPException(status_code=400, detail=f"Invalid signature: {str(e)}")

        # Handle the event
        if event["type"] == "checkout.session.completed":
            session = event["data"]["object"]

            # Get user ID and plan from metadata
            user_id = session.get("metadata", {}).get("user_id")
            plan_id = session.get("metadata", {}).get("plan_id")

            if not user_id or not plan_id:
                raise HTTPException(
                    status_code=400,
                    detail="Missing user_id or plan_id in session metadata",
                )

            # Add initial credits for the subscription
            credits_to_add = CREDITS_BY_PLAN.get(plan_id.lower())
            if credits_to_add:
                new_total = firestore.add_search_credits(user_id, credits_to_add)
                return {"status": "success", "new_credit_total": new_total}

        elif event["type"] == "customer.subscription.created":
            # Handle new subscription creation
            subscription = event["data"]["object"]
            metadata = subscription.get("metadata", {})
            user_id = metadata.get("user_id")

            if user_id:
                # Store subscription info in Firestore for tracking
                firestore.update_user_subscription(user_id, subscription.id, "active")

        elif event["type"] == "invoice.payment_succeeded":
            # Handle successful payment - add monthly credits
            invoice = event["data"]["object"]
            subscription_id = invoice.get("subscription")
            if subscription_id:
                subscription = stripe.Subscription.retrieve(subscription_id)
                user_id = subscription.get("metadata", {}).get("user_id")
                plan_id = subscription.get("metadata", {}).get("plan_id")

                if user_id and plan_id:
                    credits_to_add = CREDITS_BY_PLAN.get(plan_id.lower())
                    if credits_to_add:
                        new_total = firestore.add_search_credits(
                            user_id, credits_to_add
                        )
                        return {"status": "success", "new_credit_total": new_total}

        elif event["type"] == "customer.subscription.deleted":
            # Handle subscription cancellation
            subscription = event["data"]["object"]
            metadata = subscription.get("metadata", {})
            user_id = metadata.get("user_id")

            if user_id:
                firestore.update_user_subscription(
                    user_id, subscription.id, "cancelled"
                )

        return {"status": "success", "type": event["type"]}

    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Error processing webhook: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing webhook: {str(e)}",
        )
