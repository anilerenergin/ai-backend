from typing import Optional, List
from fastapi import FastAPI, Depends, Form, Query, UploadFile, File, HTTPException, status, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from .. import models, database, schemas, utils, fal_api, auth
from .utils import decode_token
import io
from PIL import Image
import base64
import asyncio

# Setup OAuth2
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

# Initialize DB models
models.Base.metadata.create_all(bind=database.engine)

app = FastAPI(title="AI Image Editor API")

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include auth router
app.include_router(auth.router)

# Dependency: get DB session
def get_db():
    db = database.SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Dependency: get current user from JWT
def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    email = decode_token(token)
    if not email:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = db.query(models.User).filter(models.User.email == email).first()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")

    return user

# Background task to check job status periodically
async def update_job_status(job_id: int, request_id: str, db: Session, application: str):
    """
    Background task to periodically check job status and update database
    """
    max_attempts = 120  # Check for up to 10 minutes (5 seconds * 120)
    attempt = 0
    
    while attempt < max_attempts:
        try:
            db = database.SessionLocal()
            job = db.query(models.Job).filter(models.Job.id == job_id).first()
            # Check job status
            status_result = await fal_api.check_job_status(request_id, job.application)
            print(f"Job {job_id} status: {status_result['status']}")  # Debug
            
            db = database.SessionLocal()
            job = db.query(models.Job).filter(models.Job.id == job_id).first()
            
            if job:
                job.status = status_result["status"]
                
                if status_result["status"] == "completed":
                    job.result_url = status_result.get("result_url")
                
                db.commit()
                
                # If job is completed or failed, break the loop
                if status_result["status"] in ["completed", "failed"]:
                    print(f"Job {job_id} finished with status: {status_result['status']}")
                    break
            
            db.close()
            
        except Exception as e:
            print(f"Error updating job status: {e}")
        
        # Wait 5 seconds before checking again
        await asyncio.sleep(5)
        attempt += 1
    
    print(f"Stopped monitoring job {job_id} after {attempt} attempts")

@app.post("/api/jobs", response_model=schemas.BaseResponse[schemas.JobOut])
async def create_job(
    background_tasks: BackgroundTasks,
    prompt: str = Form(..., description="Prompt for image generation or editing instructions"),
    image: Optional[UploadFile] = File(None, description="Optional image to edit (for image-to-image)"),
    strength: float = Form(0.7, description="How much to change the image (0-1) - only for image-to-image"),
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    image_bytes = None
    image_url = None
    
    # Process image if provided
    if image and image.filename:
        # Validate file type
        if not image.content_type.startswith('image/'):
            return schemas.BaseResponse(
                success=False,
                message="File must be an image",
                data=None
            )
        
        image_bytes = await image.read()
        
        # Validate file size (e.g., 10MB max)
        if len(image_bytes) > 10 * 1024 * 1024:
            return schemas.BaseResponse(
                success=False,
                message="Image too large (max 10MB)",
                data=None
            )
        
        # Validate image can be opened and get dimensions
        try:
            pil_image = Image.open(io.BytesIO(image_bytes))
            width, height = pil_image.size
            
            # Validate image dimensions
            if width < 64 or height < 64:
                return schemas.BaseResponse(
                    success=False,
                    message="Image too small (min 64x64 pixels)",
                    data=None
                )
            if width > 4096 or height > 4096:
                return schemas.BaseResponse(
                    success=False,
                    message="Image too large (max 4096x4096 pixels)",
                    data=None
                )
                
        except Exception as e:
            return schemas.BaseResponse(
                success=False,
                message=f"Invalid image file: {str(e)}",
                data=None
            )
        
        # Store original image as base64
        image_url = f"data:image/jpeg;base64,{base64.b64encode(image_bytes).decode('utf-8')}"

    try:
        # Submit job to FAL AI - this returns immediately with request_id
        fal_response = await fal_api.submit_fal_job(prompt, image_bytes)

        # Create job in database with pending status
        new_job = models.Job(
            prompt=prompt,
            image_url=image_url,  # Will be None for text-to-image
            result_url=None,  # Will be updated when job completes
            fal_request_id=fal_response.get("request_id"),
            owner_id=user.id,
            application=fal_response.get("application"),
            status="pending",  # Start with pending status
            strength=strength if image_bytes else None,  # Only store strength for image-to-image
        )

        db.add(new_job)
        db.commit()
        db.refresh(new_job)

        # Start background task to monitor job status
        background_tasks.add_task(update_job_status, new_job.id, fal_response.get("request_id"), db, new_job.application)
        
        return schemas.BaseResponse(
            success=True,
            message="Job created successfully",
            data=new_job
        )
        
    except Exception as e:
        return schemas.BaseResponse(
            success=False,
            message=f"Failed to create job: {str(e)}",
            data=None
        )

@app.get("/api/jobs/{job_id}/status", response_model=schemas.BaseResponse[dict])
async def check_job_status(
    job_id: int,
    db: Session = Depends(get_db),
    user=Depends(get_current_user)
):
    """
    Manually check the status of a specific job
    """
    job = db.query(models.Job).filter(
        models.Job.id == job_id, 
        models.Job.owner_id == user.id
    ).first()
    
    if not job:
        return schemas.BaseResponse(
            success=False,
            message="Job not found",
            data=None
        )
    
    # Initialize status_result to None
    status_result = None
    
    if job.status == "completed" and job.fal_request_id:
        # Check current status from FAL AI
        try:
            status_result = await fal_api.check_job_status(job.fal_request_id, job.application)
            
            # Update job status in database
            if status_result["status"] == "completed":
                job.status = "completed"
                job.result_url = status_result.get("result_url")
                # Only mark as failed if result_url is None for completed status
                if status_result.get("result_url") is None:
                    job.status = "failed"
            elif status_result["status"] == "failed":
                job.status = "failed"
            elif status_result["status"] == "processing":
                job.status = "processing"
            
            db.commit()
            db.refresh(job)
            
        except Exception as e:
            # If we can't check status, just return current DB status
            print(f"Error checking FAL AI status: {e}")

    # Build response data
    result_data = {
        "job_id": job.id,
        "status": job.status,
        "fal_request_id": job.fal_request_id,
    }

    # Only add result_url if status_result exists and has a non-null result_url
    if status_result and status_result.get("result_url") is not None:
        result_data["result_url"] = status_result.get("result_url")

    return schemas.BaseResponse(
        success=True,
        message="Job status retrieved successfully",
        data=result_data
    )

@app.get("/api/jobs", response_model=schemas.BaseResponse[List[schemas.JobOut]])
def list_jobs(
    page: int = Query(1, ge=1, description="Page number (starts from 1)"),
    limit: int = Query(20, ge=1, le=100, description="Number of items per page (max 100)"),
    db: Session = Depends(get_db),
    user=Depends(get_current_user)
):
    """
    Get paginated list of jobs for the current user.
    """
    skip = (page - 1) * limit
    
    jobs = db.query(models.Job)\
        .filter(models.Job.owner_id == user.id)\
        .order_by(models.Job.id.desc())\
        .offset(skip)\
        .limit(limit)\
        .all()
    
    return schemas.BaseResponse(
        success=True,
        message="Jobs retrieved successfully",
        data=jobs
    )

@app.get("/api/jobs/{job_id}", response_model=schemas.BaseResponse[schemas.JobOut])
def get_job(job_id: int, db: Session = Depends(get_db), user=Depends(get_current_user)):
    job = db.query(models.Job).filter(
        models.Job.id == job_id, 
        models.Job.owner_id == user.id
    ).first()
    
    if not job:
        return schemas.BaseResponse(
            success=False,
            message="Job not found",
            data=None
        )
    
    return schemas.BaseResponse(
        success=True,
        message="Job retrieved successfully",
        data=job
    )

@app.get("/health", response_model=schemas.BaseResponse[dict])
def health_check():
    return schemas.BaseResponse(
        success=True,
        message="Service is healthy",
        data={"status": "healthy", "service": "AI Image Editor API"}
    )

@app.get("/", response_model=schemas.BaseResponse[dict])
def read_root():
    return schemas.BaseResponse(
        success=True,
        message="AI Image Editor API is running",
        data={"message": "AI Image Editor API is running"}
    )