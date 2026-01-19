from pydantic import BaseModel
from typing import List


class AddModelRequest(BaseModel):
    model_name: str
    model_template: str
    project_name: str
    upload_model_with_sample_data: bool

class AssignModelsRequest(BaseModel):
    project_name: str
    model_names: List[str]  #project names of respective models, S_user models, project id update  -> current active project.
