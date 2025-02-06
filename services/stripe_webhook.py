import stripe
from fastapi import HTTPException, status
import logging
from services.get_secret import get_secret
import services.firestore as firestore


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

            # Determine credits based on plan
            credits_to_add = 100 if plan_id.lower() == "basic" else 500

            # Add credits to user's account
            new_total = firestore.add_search_credits(user_id, credits_to_add)

            return {"status": "success", "new_credit_total": new_total}

        return {"status": "success", "type": event["type"]}

    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Error processing webhook: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing webhook: {str(e)}",
        )
