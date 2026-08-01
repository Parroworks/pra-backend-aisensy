import requests
from fastapi import FastAPI, HTTPException, Query

app = FastAPI(title="WhatsApp Embedded Signup Backend Engine")

META_API_VERSION  = os.getenv("META_API_VERSION", "v18.0")
META_APP_ID = os.getenv("META_PHONE_NUMBER_ID")
META_APP_SECRET = os.getenv("META_ACCESS_TOKEN")
META_BASE_URL = f"https://graph.facebook.com/{META_API_VERSION}"

@app.post("/api/v1/clinic/onboard")
def onboard_client_waba(code: str = Query(..., description="The auth code from the browser redirect")):
    """
    Takes the code from the frontend/browser and provisions the WABA assets.
    """
    # ---------------------------------------------------------
    # STEP 1: Exchange temporary code for User Access Token
    # ---------------------------------------------------------
    token_url = f"{BASE_URL}/oauth/access_token"
    token_params = {
        "client_id": META_APP_ID,
        "client_secret": META_APP_SECRET,
        "code": code
    }
    
    token_response = requests.get(token_url, params=token_params)
    token_data = token_response.json()
    
    if "access_token" not in token_data:
        raise HTTPException(status_code=400, detail=f"Token Exchange Failed: {token_data}")
        
    user_access_token = token_data["access_token"]
    
    # ---------------------------------------------------------
    # STEP 2: Debug Token to fetch the shared WABA ID
    # ---------------------------------------------------------
    debug_url = f"{BASE_URL}/debug_token"
    app_token = f"{META_APP_ID}|{META_APP_SECRET}"
    debug_params = {
        "input_token": user_access_token,
        "access_token": app_token
    }
    
    debug_response = requests.get(debug_url, params=debug_params)
    debug_data = debug_response.json().get("data", {})
    
    granular_scopes = debug_data.get("granular_scopes", [])
    waba_ids = []
    
    for scope_info in granular_scopes:
        if scope_info.get("scope") == "whatsapp_business_management":
            waba_ids = scope_info.get("target_ids", [])
            break
            
    if not waba_ids:
        raise HTTPException(status_code=400, detail="No WhatsApp Business Account was shared during onboarding.")
    
    # Take the first linked WABA ID assigned to this customer session
    target_waba_id = waba_ids[0]
    
    # ---------------------------------------------------------
    # STEP 3: Query WABA to retrieve specific Phone Number IDs
    # ---------------------------------------------------------
    phone_url = f"{BASE_URL}/{target_waba_id}/phone_numbers"
    phone_headers = {
        "Authorization": f"Bearer {user_access_token}"
    }
    
    phone_response = requests.get(phone_url, headers=phone_headers)
    phone_data = phone_response.json()
    
    # ---------------------------------------------------------
    # STEP 4: Synthesize Payload for Database Storage
    # ---------------------------------------------------------
    onboarding_payload = {
        "status": "success",
        "meta_business_portfolio_id": debug_data.get("business_id"),
        "whatsapp_business_account_id": target_waba_id,
        "user_access_token": user_access_token,  # Save to securely send messages later
        "phone_numbers": []
    }
    
    for number in phone_data.get("data", []):
        onboarding_payload["phone_numbers"].append({
            "phone_number_id": number.get("id"),
            "display_phone_number": number.get("display_phone_number"),
            "quality_rating": number.get("quality_rating"),
            "status": number.get("status")
        })
        
    return onboarding_payload
