from fastapi import APIRouter, Response, Depends, UploadFile, File
from .new_database import Models_database
from fastapi import APIRouter, Response, Depends, UploadFile, File
from .new_database import Models_database
from app.PROJECTS.modals import *
from app.CORE.utility import *
from app.CORE.DB import with_master_cursor
from app.SCHEMA.schema_info import schema_info
from .models import *
from fastapi.responses import FileResponse

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
    return Models_database.create_model(
        cursor=cursor,
        payload=payload,
        owner_email=email
    )

    

@Model_router.post("/add_existing_model")
def add_existing_model(
    payload: AssignModelsRequest,
    email: str = Depends(get_current_user_email),
    cursor = Depends(with_master_cursor)
):
    return Models_database.assign_existing_models(
        cursor=cursor,
        payload=payload,
        owner_email=email
    )
    


@Model_router.post("/get_user_models")
def get_user_models(
    email: str = Depends(get_current_user_email),
    cursor = Depends(with_master_cursor)
):
    return Models_database.get_user_models(
        cursor=cursor,
        user_email=email
    )
    

@Model_router.post("/get_user_models_by_project")
def get_user_models_by_project(
    email: str = Depends(get_current_user_email),
    cursor = Depends(with_master_cursor)
):
    return Models_database.get_user_models_grouped_by_project(
        cursor=cursor,
        user_email=email
    )
    

@Model_router.post("/save_as_model")
def save_as_model(
    payload: SaveAsModelRequest,
    email: str = Depends(get_current_user_email),
    cursor = Depends(with_master_cursor)
):
    return Models_database.save_as_model(
        cursor=cursor,
        payload=payload,
        owner_email=email
    )


#
@Model_router.post("/rename_model")
def rename_model(
    payload: RenameModelRequest,
    email: str = Depends(get_current_user_email),
    cursor = Depends(with_master_cursor)
):
    return Models_database.rename_model(
        cursor=cursor,
        payload=payload,
        owner_email=email
    )


@Model_router.post("/delete_model")
def delete_model(
    payload: DeleteModelRequest,
    email: str = Depends(get_current_user_email),
    cursor = Depends(with_master_cursor)
):
    return Models_database.delete_model(
        cursor=cursor,
        payload=payload,
        owner_email=email
    )


@Model_router.post("/move_to_project")
def move_model_to_project(
    payload: MoveModelToProjectRequest,
    email: str = Depends(get_current_user_email),
    cursor = Depends(with_master_cursor)
):
    return Models_database.move_model_to_project(
        cursor=cursor,
        payload=payload,
        owner_email=email
    )


@Model_router.post("/download_model", response_class=FileResponse)
def download_model(
    payload: DownloadModelRequest,
    email: str = Depends(get_current_user_email),
    cursor = Depends(with_master_cursor)
):
    return Models_database.download_model(
        cursor=cursor,
        payload=payload,
        owner_email=email
    )


@Model_router.post("/upload")
def upload_model(
    payload: UploadModelPayload = Depends(upload_payload),
    file: UploadFile = File(...),
    email: str = Depends(get_current_user_email),
    cursor = Depends(with_master_cursor)
):
    return Models_database.upload_model(
        cursor=cursor,
        payload=payload,
        file=file,
        owner_email=email
    )


@Model_router.post("/Backup")
def upload_model(
    payload: BackupModelPayload,
    email: str = Depends(get_current_user_email),
    cursor = Depends(with_master_cursor)
):

    return Models_database.BackupModel(
        cursor=cursor,
        payload=payload,
        owner_email=email
    )

@Model_router.post("/Restore")
def upload_model(
    payload: RestoreModelPayload,
    email: str = Depends(get_current_user_email),
    cursor = Depends(with_master_cursor)
):

    return Models_database.RestoreModel(
        cursor=cursor,
        payload=payload,
        owner_email=email
    )    


@Model_router.post("/Share")
def share_model(
    payload: ShareModelPayload,
    email: str = Depends(get_current_user_email),
    cursor = Depends(with_master_cursor)
):
    return Models_database.ShareModel(
        cursor=cursor,
        payload=payload,
        owner_email=email
    )


@Model_router.post("/Get_Notifications")
def Get_Notifications(
    email: str = Depends(get_current_user_email),
    cursor = Depends(with_master_cursor)
):
    return Models_database.Get_Notifications(
        cursor=cursor,
        owner_email=email
    )

@Model_router.post("/Is_Accepted")
def is_share_model_request_accepted(
    email: str = Depends(get_current_user_email),
    cursor = Depends(with_master_cursor)
):
    return Models_database.is_share_model_request_accepted(
        cursor=cursor,
        owner_email=email
    )
