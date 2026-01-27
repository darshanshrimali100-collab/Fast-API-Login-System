from pydantic import BaseModel
from typing import List
from fastapi import Form


class AddModelRequest(BaseModel):
    model_name: str
    model_template: str
    project_name: str
    upload_model_with_sample_data: bool

class AssignModelsRequest(BaseModel):
    project_name: str
    model_names: List[str]  #project names of respective models, S_user models, project id update  -> current active project.

class SaveAsModelRequest(BaseModel):
    existing_model_name: str
    new_model_name: str
    project_name: str


class RenameModelRequest(BaseModel):
    current_model_name: str
    new_model_name: str


class DeleteModelRequest(BaseModel):
    model_name: str
    project_name: str

class MoveModelToProjectRequest(BaseModel):
    model_name: str
    project_name: str

class DownloadModelRequest(BaseModel):
    model_name: str  
    project_name: str

class UploadModelPayload(BaseModel):
    model_name: str 
    project_name: str 


def upload_payload(
    model_name: str = Form(...),
    project_name: str = Form(...)
    ):
        return UploadModelPayload(
            model_name=model_name,
            project_name=project_name
        )