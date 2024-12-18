import requests
import json
import os

from open_webui.config import (
    LITELLM_MASTER_KEY,
    LITELLM_HOST
)

BASE_URL = os.path.join(LITELLM_HOST, "key")
print(f"BASE_URL: {BASE_URL}")


async def get_subscription_info(key):
    url = f"{BASE_URL}/info"
    headers = {
        "Authorization": f"Bearer {LITELLM_MASTER_KEY}"
    }
    response = requests.get(url, params={"key": key}, headers=headers)
    response_data = response.json().get('info', {})

    if response.status_code == 200:
        max_budget = response_data.get('max_budget')
        spend = response_data.get('spend')
        budget_duration = response_data.get("budget_duration")
        return round(float(spend), 2), round(float(max_budget), 2), budget_duration
    else:
        raise Exception(f"Error getting max budget: {response.status_code}, {response.json()}")


def get_user_max_budget(key):
    """
    Get the maximum budget for a given user key, for a payment type subscription.
    """
    url = f"{BASE_URL}/info"
    headers = {
        "Authorization": f"Bearer {LITELLM_MASTER_KEY}"
    }
    response = requests.get(url, params={"key": key}, headers=headers)

    if response.status_code == 200:
        budget = response.json().get('info', {}).get('max_budget')
        spend = response.json().get('info', {}).get('spend')
        return budget - spend
    else:
        raise Exception(f"Error getting max budget: {response.status_code}, {response.json()}")

def update_user_max_budget(key, **kwargs):
    """
    Update the maximum budget for a given user key.
    """
    url = f"{BASE_URL}/update"
    headers = {
        "Authorization": f"Bearer {LITELLM_MASTER_KEY}",
        "Content-Type": "application/json"
    }
    data = {
        "key": key,
        **kwargs
    }
    response = requests.post(url, headers=headers, data=json.dumps(data))
    if response.status_code == 200:
        return response.json()
    else:
        raise Exception(f"Error updating max budget: {response.status_code}, {response.json()}")

