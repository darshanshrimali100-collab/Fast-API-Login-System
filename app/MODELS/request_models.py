from fastapi import HTTPException, APIRouter, Response, Depends
from .database import Models_database, S_MODELS_COL, S_USERMODELS_COL
from app.PROJECTS.modals import *
from app.CORE.utility import *
from app.CORE.DB import with_master_cursor
from app.SCHEMA.schema_info import schema_info
import os
import uuid
import sqlite3
from datetime import datetime
from .models import *
from app.PROJECTS.database import Projects_database
from app.CONFIG.config import DATA_FOLDER

Model_router = APIRouter(prefix="/models")


@Model_router.post("/user_templates")
def get_user_models(
    response: Response,
    email: str = Depends(get_current_user_email)
):
    schema_list = []

    for schema_name in schema_info.keys():
        schema_list.append({
            "schema_name": schema_name
        })

    return {
        "schemas": schema_list
    }

@Model_router.post("/add_new_model")
def add_new_model(
    payload: AddModelRequest,
    email: str = Depends(get_current_user_email),
    cursor = Depends(with_master_cursor)
):
    model_name = payload.model_name
    model_template = payload.model_template
    project_name = payload.project_name
    upload_model_with_sample_data = payload.upload_model_with_sample_data

    # NOTE:
    # email is the owner identifier
    owner_email = email

    # 1. Validate template
    if model_template not in schema_info:
        raise HTTPException(status_code=400, detail="Invalid model template")

    sql_file = (
        schema_info[model_template]["with_data"]
        if upload_model_with_sample_data
        else schema_info[model_template]["without_data"]
    )

    print("****** Sql_file*********** = ", sql_file)
    
    if not os.path.exists(sql_file):
        raise HTTPException(status_code=500, detail="SQL template missing")

    # 2. Create model UID + DB path
    model_uid = str(uuid.uuid4())
    db_path = os.path.join(DATA_FOLDER, f"{model_uid}.db")

    
    # 4. Insert into S_Models (EMAIL AS OWNER)
    try:
        result = Models_database.add_model(cursor, model_uid, model_name, db_path, owner_email)
    except Exception:
        raise HTTPException(status_code=409, detail="Model already exists")
    
    if result == True: 
        # insert details to S_UserModels
        project_id = Projects_database.get_project_id_for_user(cursor, email, project_name)
        model_id = Models_database.get_model_id_by_name(cursor, model_name)

        if project_id & model_id:
            Models_database.insert_user_model(cursor, model_id, email, project_id)
        else:
            raise HTTPException(status_code=400, detail=f"details not found model_name = {model_name}, project_name = {project_name}")

        # 3. Create SQLite DB from SQL file
        try:
            with sqlite3.connect(db_path) as model_db:
                with open(sql_file, "r") as f:
                    model_db.executescript(f.read())
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"DB creation failed: {str(e)}")
    else:
        raise HTTPException(status_code=500, detail="DB operation failed")

    return {
        #"model_uid": model_uid,
        "model_name": model_name,
        "project_name": project_name,
        #"model_path": db_path,
        "owner": owner_email,
        "created_at": datetime.now(timezone.utc).isoformat()
    }

#add_existing_model
@Model_router.post("/add_existing_model")
def add_existing_model(
    payload: AssignModelsRequest,
    email: str = Depends(get_current_user_email),
    cursor = Depends(with_master_cursor)
):
    if not payload.model_names:
        raise HTTPException(status_code=400, detail="No models provided")

    active_project_id = Projects_database.get_curent_active_project_id_by_email(cursor, email)
    print("*******************************", active_project_id)

    for model_name in payload.model_names:

        model_id = Models_database.get_model_id_by_name(cursor, model_name)
        if not model_id:
            continue  # silently skip, as per your requirement

        Models_database.assign_model_to_user(
            cursor,
            model_id,
            email,
            active_project_id[0]
        )

    return {"message": "updated successfully"}


@Model_router.post("/get_user_models")
def get_user_models(
    email: str = Depends(get_current_user_email),
    cursor = Depends(with_master_cursor)
):
    user_email = email

    rows = Models_database.get_models_by_email(cursor, user_email)

    if not rows:
        raise HTTPException(
            status_code=404,
            detail=f"No models found for user: {user_email}"
        )

    models = []
    for row in rows:
        models.append({
            "model_name": row[0],
            #"model_uid": row[1]
        })

    return {
        "user": user_email,
        "models": models
    }
