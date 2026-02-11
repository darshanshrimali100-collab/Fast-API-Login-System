from pydantic import BaseModel,field_validator
from typing import List, Dict
from pydantic import BaseModel,field_validator
from typing import List, Dict
from fastapi import Form

#extend base class for project_name and model_name.

class AddModelRequest(BaseModel):
    model_name: str
    model_template: str
    project_name: str
    upload_model_with_sample_data: bool

    @field_validator(
        "model_name",
        "model_template",
        "project_name"
    )
    @classmethod
    def non_empty_strings(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Model name and project name and model template are required")
        return v.strip()

    
class AssignModelsRequest(BaseModel):
    target_project: str
    models_by_project: Dict[str, List[str]]

    @field_validator("target_project")
    @classmethod
    def validate_target_project(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Current project name is required")
        return v

    @field_validator("models_by_project")
    @classmethod
    def validate_models_by_project(cls, v: dict) -> dict:
        if not v:
            raise ValueError("No models provided")
        return v
    target_project: str
    models_by_project: Dict[str, List[str]]


class SaveAsModelRequest(BaseModel):
    current_project_name: str
    existing_model_name: str
    new_model_name: str
    project_name: str

    @field_validator(
        "current_project_name",
        "existing_model_name",
        "new_model_name",
        "project_name"
    )
    @classmethod
    def non_empty_strings(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Model name and project name are required")
        return v.strip()

    


class RenameModelRequest(BaseModel):
    current_project_name: str
    current_model_name: str
    new_model_name: str

    @field_validator(
        "current_project_name",
        "current_model_name",
        "new_model_name"
    )
    @classmethod
    def non_empty_strings(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Model name and project name are required")
        return v.strip()

    


class DeleteModelRequest(BaseModel):
    current_project_name: str
    model_name: str
    project_name: str

    @field_validator(
        "current_project_name",
        "model_name",
        "project_name"
    )
    @classmethod
    def non_empty_strings(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("current project name , Model name and project name are required")
        return v.strip()

    

class MoveModelToProjectRequest(BaseModel):
    current_project_name: str
    model_name: str
    project_name: str

    @field_validator(
        "current_project_name",
        "model_name",
        "project_name"
    )
    @classmethod
    def non_empty_strings(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("current project name , Model name and project name are required")
        return v.strip()

    

class DownloadModelRequest(BaseModel):
    current_project_name: str
    model_name: str  
    project_name: str

    @field_validator(
        "current_project_name",
        "model_name",
        "project_name"
    )
    @classmethod
    def non_empty_strings(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("current project name , Model name and project name are required")
        return v.strip()

    
class UploadModelPayload(BaseModel):
    current_project_name: str
    model_name: str 
    project_name: str 

    @field_validator(
        "current_project_name",
        "model_name",
        "project_name"
    )
    @classmethod
    def non_empty_strings(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("current project name , Model name and project name are required")
        return v.strip()


def upload_payload(
    current_project_name: str = Form(...),
    model_name: str = Form(...),
    project_name: str = Form(...)
    ):
        return UploadModelPayload(
            current_project_name = current_project_name,
            model_name=model_name,
            project_name=project_name
        )

class BackupModelPayload(BaseModel):
    current_project_name: str
    model_name: str 
    user_comment: str

    @field_validator(
        "current_project_name",
        "model_name",
        "user_comment"
    )
    @classmethod
    def non_empty_strings(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("current project name , Model name and project name are required")
        return v.strip()

class RestoreModelPayload(BaseModel):
    current_project_name: str
    model_name: str 
    Backup_id: str

    @field_validator(
        "current_project_name",
        "model_name",
        "Backup_id"
    )
    @classmethod
    def non_empty_strings(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("current project name , Model name and project name are required")
        return v.strip()


class ShareModelPayload(BaseModel):
    touser_email: str
    modelname: str
    project_name: str
    access_level: str   # e.g. "read", "write"
    title: str
    message: str

    @field_validator(
        "touser_email",
        "modelname",
        "project_name",
        "access_level",
        "title",
        "message"
    )
    @classmethod
    def non_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("All fields are required")
        return v.strip()

