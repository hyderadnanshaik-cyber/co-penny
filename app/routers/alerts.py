from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import Optional
from app.services.email_service import EmailService

router = APIRouter(prefix="/alerts", tags=["alerts"])
email_service = EmailService()

class AlertRequest(BaseModel):
    email: str
    message: str

@router.post("/test")
def test_alert(req: AlertRequest):
    """
    Send a test email alert.
    """
    if not email_service.enabled:
        raise HTTPException(status_code=503, detail="Email service is not configured (SMTP credentials missing)")
    
    success = email_service.send_alert(
        to_email=req.email,
        subject="Co Penny Advisor - Test Alert",
        body=f"This is a test alert from your Copilot.\n\nMessage: {req.message}"
    )
    
    if success:
        return {"status": "success", "message": f"Email sent to {req.email}"}
    else:
        raise HTTPException(status_code=500, detail="Failed to send email")
