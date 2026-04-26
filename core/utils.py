from django.shortcuts import render
from api_management.models import *
from .models import Favorite


def check_and_increment_global_quota(user, api):
    """
    Checks and increments the user's quota based on the API cost.
    
    Args:
        user: The user making the request
        api: The API instance being called
    
    Returns:
        tuple: (success: bool, message: str)
    """
    quota = APICallQuota.get_or_create_for_user(user)
    cost = api.quota_cost
    
    # Check if the user has enough credits
    if not quota.has_sufficient_quota(cost):
        remaining = quota.remaining_calls
        message = (
            f"Insufficient quota. This API costs {cost} credit{'s' if cost > 1 else ''}, "
            f"but you only have {remaining} credit{'s' if remaining > 1 else ''} left."
        )
        return False, message
    
    # Increment usage based on the API cost
    quota.increment_call_count(cost)
    
    remaining = quota.remaining_calls
    message = (
        f"Call successful. Cost: {cost} credit{'s' if cost > 1 else ''}. "
        f"You now have {remaining} remaining."
    )
    return True, message


def is_user_favorited(api, user):
    if not user.is_authenticated:
        return False
    return Favorite.objects.filter(user=user, api=api).exists()
