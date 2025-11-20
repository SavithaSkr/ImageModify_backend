import httpx
from app.config import settings


AUTOMATION_URL = settings.AUTOMATION_API_URL  # Example: http://localhost:9001/run


async def trigger_automation(user_api_key: str) -> bool:
    """
    Calls automation microservice and triggers image processing.
    This API key is user-specific and checked by the automation server.
    """

    headers = {
        "x-api-key": user_api_key
    }

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(AUTOMATION_URL, headers=headers)

        return response.status_code == 200

    except Exception as e:
        print("Automation Trigger Error:", e)
        return False
