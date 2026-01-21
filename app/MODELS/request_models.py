import shutil
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

    project_id = Projects_database.get_project_id_for_user(cursor, email, project_name)
    
    if Models_database.model_exists_in_project(cursor, project_id, model_name):
        raise HTTPException(status_code=400, detail=f"model already exits, model_name = {model_name}, project_name = {project_name}")
    
    # 4. Insert into S_Models (EMAIL AS OWNER)
    try:
        result = Models_database.add_model(cursor, model_uid, model_name, db_path, owner_email)
    except Exception:
        raise HTTPException(status_code=409, detail="Model already exists")
    
    if result == True: 
        # insert details to S_UserModels
        model_id = Models_database.get_model_id_by_name(cursor, model_name, model_uid)

        if project_id and model_id:
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
    if not payload.project_name:
        raise HTTPException(status_code=400, detail="No Project name provided")

    if not payload.model_names:
        raise HTTPException(status_code=400, detail="No models provided")

    result = Models_database.assign_project_to_models(cursor, email, payload.model_names, payload.project_name)

    if result == None:
        raise HTTPException(status_code=400, detail="No models updated")

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


@Model_router.post("/get_user_models_by_project")
def get_user_models_by_project(
    email: str = Depends(get_current_user_email),
    cursor = Depends(with_master_cursor)
):
    user_email = email

    rows = Models_database.get_models_by_user_grouped(cursor, user_email)

    if not rows:
        raise HTTPException(
            status_code=404,
            detail=f"No models found for user: {user_email}"
        )

    result = {}

    for row in rows:
        project_name = row[0]
        model_name = row[1]

        if project_name not in result:
            result[project_name] = []

        result[project_name].append(model_name)

    return result


@Model_router.post("/save_as_model")
def save_as_model(
    payload: SaveAsModelRequest,
    email: str = Depends(get_current_user_email),
    cursor = Depends(with_master_cursor)
):
    existing_name = payload.existing_model_name.strip()
    new_name = payload.new_model_name.strip()
    project_name = payload.project_name.strip()

    if not existing_name or not new_name or not project_name:
        raise HTTPException(400, "Model name and project name are required")

    #  Resolve project_id
    project_id = Projects_database.get_project_id_for_user(
        cursor,
        email,
        project_name
    )

    if not project_id:
        raise HTTPException(404, "Project not found")

    #  Fetch existing model from SAME project
    existing = Models_database.get_model_by_name_and_project(
        cursor,
        email,
        existing_name,
        project_id
    )

    if not existing:
        raise HTTPException(
            404,
            f"Model '{existing_name}' not found in project '{project_name}'"
        )

    old_db_path = existing["ModelPath"]

    if not os.path.exists(old_db_path):
        raise HTTPException(500, "Source DB file missing")

    #  Duplicate name check in same project
    if Models_database.model_exists_in_project(
        cursor,
        project_id,
        new_name
    ):
        raise HTTPException(
            400,
            f"Model '{new_name}' already exists in this project"
        )

    #  Create new UID + DB path
    new_uid = str(uuid.uuid4())
    new_db_path = os.path.join(DATA_FOLDER, f"{new_uid}.db")

    try:
        shutil.copyfile(old_db_path, new_db_path)
    except Exception as e:
        raise HTTPException(500, f"DB copy failed: {str(e)}")

    #  Insert into S_Models
    Models_database.add_model(
        cursor,
        new_uid,
        new_name,
        new_db_path,
        email
    )

    model_id = Models_database.get_model_id_by_name(cursor, new_name, new_uid)
    if not model_id:
        raise HTTPException(500, "Model insert failed")

    #  Map to SAME project
    Models_database.insert_user_model(
        cursor,
        model_id,
        email,
        project_id
    )

    return {
        "message": "Model saved as new model successfully",
        "source_model": existing_name,
        "new_model": new_name,
        "project": project_name
    }
