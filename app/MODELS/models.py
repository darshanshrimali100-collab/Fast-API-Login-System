from pydantic import BaseModel,field_validator, ValidationInfo
from typing import List, Dict
from fastapi import Form

#extend base class for project_name and model_name.

class NonEmptyStrModel(BaseModel):

    @field_validator("*", mode="before")
    @classmethod
    def strip_and_validate(cls, v, info: ValidationInfo):

        if info.field_name == "Save_as_From_User_Email":
            return v

        if isinstance(v, str):
            v = v.strip()
            if not v:
                raise ValueError(f"{cls.__name__}: empty string not allowed")
        return v

class ModelProjectPayload(NonEmptyStrModel):
    model_name: str
    project_name: str

class NotificationIdPayload(NonEmptyStrModel):
    notification_id: str

class AddModelRequest(ModelProjectPayload):
    model_template: str
    upload_model_with_sample_data: bool


    
class AssignModelsRequest(NonEmptyStrModel):
    target_project: str
    models_by_project: Dict[str, List[str]]


class SaveAsModelRequest(ModelProjectPayload):
    new_model_name: str
    Save_as_From_User_Email: str


class RenameModelRequest(ModelProjectPayload):
    new_model_name: str
    

class DeleteModelRequest(ModelProjectPayload):
    pass
    

class MoveModelToProjectRequest(ModelProjectPayload):
    current_project_name: str
    

class DownloadModelRequest(ModelProjectPayload):
    pass
    
class UploadModelPayload(ModelProjectPayload):
    pass


def upload_payload(
    model_name: str = Form(...),
    project_name: str = Form(...)
    ):
        return UploadModelPayload(
            model_name=model_name,
            project_name=project_name
        )

class BackupModelPayload(ModelProjectPayload):
    user_comment: str


class RestoreModelPayload(ModelProjectPayload):
    Backup_id: str


class ShareModelPayload(ModelProjectPayload):
    touser_email: str
    access_level: str   


class ModelBackupPayload(ModelProjectPayload):
    pass

class IsAcceptedModelPayload(ModelProjectPayload):
    notification_id: str
    new_project: str    
    From_user_email: str


class RejectModelSharePayload(NotificationIdPayload):
    pass


class CancelModelSharePayload(NotificationIdPayload):
    pass


