from fastapi import APIRouter, Depends, HTTPException, status, Form
from sqlalchemy.orm import Session
from app import models, database, utils, schemas


router = APIRouter(prefix="/auth", tags=["Authentication"])


# Dependency for DB session
def get_db():
    db = database.SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.post("/register", response_model=schemas.BaseResponse[dict])
def register(
    email: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db)
):
    try:
        # Validate email format
        if not utils.is_valid_email(email):
            return schemas.BaseResponse(
                success=False,
                message="Invalid email format",
                data=None
            )
        
        # Validate password strength
        if len(password) < 6:
            return schemas.BaseResponse(
                success=False,
                message="Password must be at least 6 characters long",
                data=None
            )

        existing_user = db.query(models.User).filter(models.User.email == email).first()
        if existing_user:
            return schemas.BaseResponse(
                success=False,
                message="Email already registered",
                data=None
            )

        hashed_pw = utils.hash_password(password)
        new_user = models.User(email=email, hashed_password=hashed_pw)
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
        
        # Create access token for the new user
        access_token = utils.create_access_token(data={"sub": new_user.email})
        
        return schemas.BaseResponse(
            success=True,
            message="User registered successfully",
            data={
                "access_token": access_token,
                "token_type": "bearer",
                "user_id": new_user.id,
                "email": new_user.email
            }
        )
    
    except Exception as e:
        db.rollback()
        return schemas.BaseResponse(
            success=False,
            message=f"Registration failed: {str(e)}",
            data=None
        )
@router.post("/login", response_model=schemas.BaseResponse[dict])
def login(
    username: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db)
):
    try:
        user = db.query(models.User).filter(models.User.email == username).first()
        if not user or not utils.verify_password(password, user.hashed_password):
            return schemas.BaseResponse(
                success=False,
                message="Invalid credentials",
                data=None
            )

        access_token = utils.create_access_token(data={"sub": user.email})
        
        return schemas.BaseResponse(
            success=True,
            message="Login successful",
            data={
                "access_token": access_token, 
                "token_type": "bearer",
                "user_id": user.id,
                "email": user.email
            }
        )
    
    except Exception as e:
        return schemas.BaseResponse(
            success=False,
            message=f"Login failed: {str(e)}",
            data=None
        )