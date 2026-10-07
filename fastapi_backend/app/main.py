from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from .database import engine, Base
from .models.payment import Payment
from .routers.payments import router as payments_router
from .routers.dashboard import router as dashboard_router


app = FastAPI(
    title="Credit Card Payment System - Payment API",
    description="FastAPI service for payment processing",
    version="1.0.0",
)


# ---------------------------------------------------------
# CORS
# ---------------------------------------------------------
# Allows the React frontend running on port 5173
# to communicate with the FastAPI payment service on port 8001.
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------
# Create FastAPI database tables
# ---------------------------------------------------------
Base.metadata.create_all(bind=engine)


# ---------------------------------------------------------
# Payment router
# ---------------------------------------------------------
app.include_router(payments_router)


# ---------------------------------------------------------
# Dashboard router
# ---------------------------------------------------------
app.include_router(dashboard_router)


# ---------------------------------------------------------
# Root
# ---------------------------------------------------------
@app.get("/")
def root():
    return {
        "message": "Credit Card Payment API is running"
    }


# ---------------------------------------------------------
# Health check
# ---------------------------------------------------------
@app.get("/health")
def health_check():
    return {
        "status": "healthy"
    }


# ---------------------------------------------------------
# Database health check
# ---------------------------------------------------------
@app.get("/database-health")
def database_health():
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))

        return {
            "status": "healthy",
            "database": "connected"
        }

    except Exception as e:
        return {
            "status": "error",
            "database": "connection failed",
            "detail": str(e)
        }