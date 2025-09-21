from fastapi import FastAPI, APIRouter, HTTPException
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field
from typing import List, Optional
import uuid
from datetime import datetime, timedelta, timezone
from enum import Enum

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# Create the main app without a prefix
app = FastAPI()

# Create a router with the /api prefix
api_router = APIRouter(prefix="/api")

# Enums
class PersonType(str, Enum):
    JOAN = "joan"
    MERY = "mery"
    PACO = "paco"
    BELEN = "belen"

class AreaType(str, Enum):
    COCINA = "cocina"
    SALON_PASILLO = "salon_pasillo"
    BANO_JOAN_MERY = "bano_joan_mery"
    BANO_PACO_BELEN = "bano_paco_belen"

class TaskType(str, Enum):
    LIMPIEZA_PRINCIPAL = "limpieza_principal"
    LIMPIEZA_BANO = "limpieza_bano"

# Models
class PersonTask(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    week_start: str  # ISO format date string
    person: PersonType
    area: AreaType
    task_type: TaskType
    limpieza_completada: bool = False
    completed_at: Optional[str] = None

class WeekSchedule(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    week_start: str  # ISO format date string (Monday)
    week_end: str   # ISO format date string (Sunday)
    week_number: int
    year: int
    joan_area: AreaType
    mery_area: AreaType
    paco_area: AreaType
    belen_area: AreaType
    joan_bano: bool  # True if Joan cleans bathroom this week
    mery_bano: bool  # True if Mery cleans bathroom this week
    paco_bano: bool  # True if Paco cleans bathroom this week
    belen_bano: bool # True if Belén cleans bathroom this week
    tasks: List[PersonTask] = []

class TaskCompletionUpdate(BaseModel):
    week_start: str
    person: PersonType
    area: AreaType
    task_type: TaskType
    completed: bool

# Helper functions
def get_monday_of_week(date):
    """Get the Monday of the week for a given date"""
    days_since_monday = date.weekday()
    monday = date - timedelta(days=days_since_monday)
    return monday

def get_sunday_of_week(date):
    """Get the Sunday of the week for a given date"""
    monday = get_monday_of_week(date)
    sunday = monday + timedelta(days=6)
    return sunday

def get_next_monday():
    """Get next Monday's date"""
    today = datetime.now(timezone.utc).date()
    days_until_monday = (7 - today.weekday()) % 7
    if days_until_monday == 0:  # If today is Monday, get next Monday
        days_until_monday = 7
    return today + timedelta(days=days_until_monday)

def generate_all_schedules():
    """Generate schedules from next week until July 1, 2026"""
    schedules = []
    start_date = get_next_monday()
    end_date = datetime(2026, 7, 1).date()
    
    current_date = start_date
    week_counter = 0
    
    while current_date <= end_date:
        monday = current_date
        sunday = get_sunday_of_week(monday)
        
        # Determine main area assignments (alternating each week)
        # Joan & Mery always work together, Paco & Belén always work together
        if week_counter % 2 == 0:
            joan_area = mery_area = AreaType.COCINA
            paco_area = belen_area = AreaType.SALON_PASILLO
        else:
            joan_area = mery_area = AreaType.SALON_PASILLO
            paco_area = belen_area = AreaType.COCINA
        
        # Determine bathroom assignments (alternating each week, independent of main areas)
        # Joan & Mery alternate their bathroom, Paco & Belén alternate their bathroom
        joan_bano = (week_counter % 2 == 0)  # Joan cleans on even weeks
        mery_bano = (week_counter % 2 == 1)  # Mery cleans on odd weeks
        paco_bano = (week_counter % 2 == 0)  # Paco cleans on even weeks
        belen_bano = (week_counter % 2 == 1) # Belén cleans on odd weeks
        
        # Create tasks for each person
        tasks = []
        
        # Main area tasks (everyone has one)
        for person, area in [
            (PersonType.JOAN, joan_area),
            (PersonType.MERY, mery_area), 
            (PersonType.PACO, paco_area),
            (PersonType.BELEN, belen_area)
        ]:
            tasks.append(PersonTask(
                week_start=monday.isoformat(),
                person=person,
                area=area,
                task_type=TaskType.LIMPIEZA_PRINCIPAL
            ))
        
        # Bathroom tasks (only for assigned person each week)
        if joan_bano:
            tasks.append(PersonTask(
                week_start=monday.isoformat(),
                person=PersonType.JOAN,
                area=AreaType.BANO_JOAN_MERY,
                task_type=TaskType.LIMPIEZA_BANO
            ))
        
        if mery_bano:
            tasks.append(PersonTask(
                week_start=monday.isoformat(),
                person=PersonType.MERY,
                area=AreaType.BANO_JOAN_MERY,
                task_type=TaskType.LIMPIEZA_BANO
            ))
        
        if paco_bano:
            tasks.append(PersonTask(
                week_start=monday.isoformat(),
                person=PersonType.PACO,
                area=AreaType.BANO_PACO_BELEN,
                task_type=TaskType.LIMPIEZA_BANO
            ))
        
        if belen_bano:
            tasks.append(PersonTask(
                week_start=monday.isoformat(),
                person=PersonType.BELEN,
                area=AreaType.BANO_PACO_BELEN,
                task_type=TaskType.LIMPIEZA_BANO
            ))
        
        schedule = WeekSchedule(
            week_start=monday.isoformat(),
            week_end=sunday.isoformat(),
            week_number=monday.isocalendar()[1],
            year=monday.year,
            joan_area=joan_area,
            mery_area=mery_area,
            paco_area=paco_area,
            belen_area=belen_area,
            joan_bano=joan_bano,
            mery_bano=mery_bano,
            paco_bano=paco_bano,
            belen_bano=belen_bano,
            tasks=tasks
        )
        
        schedules.append(schedule)
        current_date += timedelta(days=7)
        week_counter += 1
    
    return schedules

@api_router.get("/")
async def root():
    return {"message": "Casa Limpia API - ¡Tu planificador de limpieza doméstica con baños incluidos!"}

@api_router.post("/generate-schedules")
async def create_schedules():
    """Generate all schedules from next week to July 2026"""
    try:
        # Delete existing schedules to regenerate with new bathroom structure
        await db.week_schedules.delete_many({})
        
        schedules = generate_all_schedules()
        
        # Insert all schedules
        schedule_dicts = [schedule.dict() for schedule in schedules]
        result = await db.week_schedules.insert_many(schedule_dicts)
        
        return {
            "message": f"Se crearon {len(result.inserted_ids)} planificaciones semanales con baños incluidos",
            "created": len(result.inserted_ids),
            "from": schedules[0].week_start if schedules else None,
            "to": schedules[-1].week_start if schedules else None
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error creando planificaciones: {str(e)}")

@api_router.get("/current-week", response_model=WeekSchedule)
async def get_current_week():
    """Get current week's schedule or the first available schedule if current week doesn't exist"""
    try:
        today = datetime.now(timezone.utc).date()
        monday = get_monday_of_week(today)
        
        # First try to find the current week
        schedule = await db.week_schedules.find_one({"week_start": monday.isoformat()})
        
        # If current week doesn't exist, get the first available schedule (next week or later)
        if not schedule:
            schedule = await db.week_schedules.find_one({}, sort=[("week_start", 1)])
            if not schedule:
                raise HTTPException(status_code=404, detail="No hay planificaciones disponibles")
        
        return WeekSchedule(**schedule)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error obteniendo semana actual: {str(e)}")

@api_router.post("/complete-task")
async def complete_task(task_update: TaskCompletionUpdate):
    """Mark a person's specific task as completed or uncompleted"""
    try:
        filter_query = {
            "week_start": task_update.week_start,
            "tasks": {
                "$elemMatch": {
                    "person": task_update.person.value,
                    "area": task_update.area.value,
                    "task_type": task_update.task_type.value
                }
            }
        }
        
        completed_at = datetime.now(timezone.utc).isoformat() if task_update.completed else None
        
        update_query = {
            "$set": {
                "tasks.$.limpieza_completada": task_update.completed,
                "tasks.$.completed_at": completed_at
            }
        }
        
        result = await db.week_schedules.update_one(filter_query, update_query)
        
        if result.matched_count == 0:
            raise HTTPException(status_code=404, detail="Tarea no encontrada")
        
        return {"message": "Tarea actualizada correctamente", "completed": task_update.completed}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error actualizando tarea: {str(e)}")

@api_router.get("/schedules", response_model=List[WeekSchedule])
async def get_all_schedules():
    """Get all schedules (for debugging)"""
    try:
        schedules = await db.week_schedules.find().sort("week_start", 1).to_list(length=None)
        return [WeekSchedule(**schedule) for schedule in schedules]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error obteniendo planificaciones: {str(e)}")

@api_router.delete("/schedules")
async def delete_all_schedules():
    """Delete all schedules (for debugging)"""
    try:
        result = await db.week_schedules.delete_many({})
        return {"message": f"Se eliminaron {result.deleted_count} planificaciones"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error eliminando planificaciones: {str(e)}")

# Include the router in the main app
app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()