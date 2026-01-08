from pydantic import BaseModel, Field

class CreateProjectRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    open_after_create: bool

class OpenProjectRequest(BaseModel):
    project_id: str

class RenameProjectRequest(BaseModel):
    project_id: str
    new_name: str = Field(..., min_length=1, max_length=100)

class DeleteProjectRequest(BaseModel):
    project_id: str
    confirm_name: str

class ChangeProjectRequest(BaseModel):
    modal: str
    current_project_id: str
    new_project_id: str
