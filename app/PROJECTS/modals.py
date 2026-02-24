from pydantic import BaseModel, Field


class CreateProjectRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=100, description= "Project Length Must be Less Than 100")
    open_after_create: bool


class OpenProjectRequest(BaseModel):
    project_name: str = Field(..., min_length=1, max_length=100)


class RenameProjectRequest(BaseModel):
    project_name: str = Field(..., min_length=1, max_length=100)
    new_name: str = Field(..., min_length=1, max_length=100)


class DeleteProjectRequest(BaseModel):
    project_name: str = Field(..., min_length=1, max_length=100)
    confirm_name: str = Field(..., min_length=1, max_length=100)


class ChangeProjectRequest(BaseModel):
    modal: str
    new_project_name: str = Field(..., min_length=1, max_length=100)
