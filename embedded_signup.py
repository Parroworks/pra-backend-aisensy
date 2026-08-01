import requests
from fastapi import FastAPI, HTTPException, Query

app = FastAPI(title="WhatsApp Embedded Signup Backend Engine")

META_API_VERSION  = os.getenv("META_API_VERSION", "v18.0")
META_APP_ID = os.getenv("META_PHONE_NUMBER_ID")
META_APP_SECRET = os.getenv("META_ACCESS_TOKEN")
META_BASE_URL = f"https://graph.facebook.com/{META_API_VERSION}"

# Supabase Storage Setup
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_KEY")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)


@app.post("/api/v1/clinic/onboard")
def onboard_clinic_waba(
    code: str = Query(..., description="Temporary code from frontend/browser redirect"),
    clinic_name: str = Query(..., description="Internal tracking name for the clinic")
):
    """
    Onboards a clinic by exchanging the short-lived token to extract permanent asset IDs,
    saving them to Supabase, and discarding the temporary token immediately.
    """
    # -------------------------------------------------------------------------
    # Exchange temporary code for the short-lived User Access Token
    # -------------------------------------------------------------------------
    token_url = f"{BASE_URL}/oauth/access_token"
    token_params = {"client_id": META_APP_ID, "client_secret": META_APP_SECRET, "code": code}
    
    try:
        token_response = requests.get(token_url, params=token_params)
        token_data = token_response.json()
    except requests.RequestException as e:
        raise HTTPException(status_code=500, detail=f"Meta network exchange error: {str(e)}")
    
    if "access_token" not in token_data:
        raise HTTPException(status_code=400, detail=f"Invalid or expired registration code: {token_data}")
        
    # The temporary token used ONLY for asset exploration
    temporary_user_token = token_data["access_token"]
    
    # -------------------------------------------------------------------------
    # Use temporary token to extract the permanent WABA ID
    # -------------------------------------------------------------------------
    debug_url = f"{BASE_URL}/debug_token"
    debug_params = {"input_token": temporary_user_token, "access_token": f"{META_APP_ID}|{META_APP_SECRET}"}
    
    try:
        debug_response = requests.get(debug_url, params=debug_params)
        debug_data = debug_response.json().get("data", {})
    except requests.RequestException as e:
        raise HTTPException(status_code=500, detail=f"Error parsing token attributes: {str(e)}")
    
    granular_scopes = debug_data.get("granular_scopes", [])
    target_waba_id = None
    
    for scope_info in granular_scopes:
        if scope_info.get("scope") == "whatsapp_business_management":
            waba_ids = scope_info.get("target_ids", [])
            if waba_ids:
                target_waba_id = waba_ids[0]  # Grab the core structural string ID
            break
            
    if not target_waba_id:
        raise HTTPException(status_code=400, detail="No authorized WhatsApp Business Account found.")
    
    # -------------------------------------------------------------------------
    # Use temporary token one last time to read verified Phone Line IDs
    # -------------------------------------------------------------------------
    phone_url = f"{BASE_URL}/{target_waba_id}/phone_numbers"
    phone_headers = {"Authorization": f"Bearer {temporary_user_token}"}
    
    try:
        phone_response = requests.get(phone_url, headers=phone_headers)
        phone_data = phone_response.json()
    except requests.RequestException as e:
        raise HTTPException(status_code=500, detail=f"Error inspecting verified phone assets: {str(e)}")
    
    # -------------------------------------------------------------------------
    # Store permanent IDs in Supabase and discard the temporary token
    # -------------------------------------------------------------------------
    try:
        account_payload = {
            "clinic_name": clinic_name,
            "meta_business_portfolio_id": debug_data.get("business_id"),
            "whatsapp_business_account_id": target_waba_id
        }
        
        account_result = (
            supabase.table("clinic_whatsapp_accounts")
            .upsert(account_payload, on_conflict="whatsapp_business_account_id")
            .execute()
        )
        db_account_id = account_result.data[0]["id"]
        
        saved_numbers = []
        for number in phone_data.get("data", []):
            phone_payload = {
                "whatsapp_account_id": db_account_id,
                "phone_number_id": number.get("id"),
                "display_phone_number": number.get("display_phone_number"),
                "quality_rating": number.get("quality_rating"),
                "status": number.get("status")
            }
            phone_result = (
                supabase.table("clinic_whatsapp_numbers")
                .upsert(phone_payload, on_conflict="phone_number_id")
                .execute()
            )
            saved_numbers.append(phone_result.data[0]["phone_number_id"])
            
    except Exception as db_err:
        raise HTTPException(status_code=500, detail=f"Database persistent write error: {str(db_err)}")
        
    return {
        "status": "success",
        "message": f"Successfully mapped asset channels for {clinic_name}.",
        "saved_waba_id": target_waba_id,
        "saved_phone_number_ids": saved_numbers
    }
