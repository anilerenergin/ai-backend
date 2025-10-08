import os
import fal_client
from fastapi import HTTPException
import asyncio
import base64

# Load FAL API key from environment variables
FAL_API_KEY = os.getenv("FAL_KEY")

async def submit_fal_job(prompt: str, image_bytes: bytes = None) -> dict:
    """
    Submit a job to FAL AI and return request_id immediately
    The actual processing happens asynchronously
    """
    if not FAL_API_KEY:
        raise HTTPException(status_code=500, detail="FAL API key not configured")
    
    try:
        # Determine which endpoint to use based on whether image is provided
        if image_bytes:
            # Image-to-image: use Nano Banana Edit
            endpoint = "fal-ai/nano-banana/edit"
            
            # Convert image to base64
            image_base64 = base64.b64encode(image_bytes).decode('utf-8')
            
            arguments = {
                "prompt": prompt,
                "image_urls": [f"data:image/jpeg;base64,{image_base64}"],
                "num_images": 1,
                "output_format": "jpeg"
            }
        else:
            # Text-to-image: use Nano Banana Text to Image
            endpoint = "fal-ai/nano-banana"
            
            arguments = {
                "prompt": prompt,
                "num_images": 1,
                "output_format": "jpeg",
                "aspect_ratio": "1:1"
            }
        
        # Submit the job to FAL AI - this returns immediately with request_id
        handler = fal_client.submit(endpoint, arguments=arguments)
        
        # Return immediately with request_id - processing happens in background
        return {
            "request_id": handler.request_id,
            "status": "submitted",
            "application": endpoint
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to submit job to AI service: {str(e)}"
        )

async def check_job_status(request_id: str,application:str) -> dict:
    """
    Check the status of a submitted job and get result if completed
    """
    if not FAL_API_KEY:
        raise HTTPException(status_code=500, detail="FAL API key not configured")

    try:
        # First, check the status using the status method
        current_status = fal_client.status(application,request_id)
        
        if current_status.__class__ == fal_client.Completed:
            
            # Job is completed, get the result
            try:
          
                result = fal_client.result(application,request_id)

                return {
                    "status": "completed",
                    "result_url": result.get("images", [{}])[0].get("url") if result.get("images") else None,
                    "description": result.get("description", ""),
                    "result_data": result
                }
            except Exception as result_error:
                return {
                    "status": "failed",  # Status says completed but can't get result
                    "result_url": None,
                    "error": f"Job marked as completed but result unavailable: {str(result_error)}"
                }
                
        elif current_status.__class__ == fal_client.InProgress:
            return {
                "status": "processing",
                "message": "Job is currently being processed"
            }

        elif current_status.__class__ == fal_client.Queued:
            return {
                "status": "queued",
                "message": "Job is in queue waiting to start"
            }
        else:
            return {
                "status": "pending",
                "message": f"Job status: pending"
            }
            
    except Exception as e:
        print(f"Error checking job status: {str(e)}")  # Debug log
        # If we can't get status, try the result method as fallback
        try:
            result = fal_client.result(application,request_id)
            return {
                "status": "completed",
                "result_url": result.get("images", [{}])[0].get("url") if result.get("images") else None,
                "description": result.get("description", ""),
            }
        except Exception as result_error:
            # If both methods fail, return pending
            return {
                "status": "pending",
                "error": f"Unable to determine job status: {str(e)}"
            }