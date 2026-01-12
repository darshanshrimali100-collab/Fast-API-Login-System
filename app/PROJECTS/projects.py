from fastapi import HTTPException, status, APIRouter, Body, Response, Cookie, Depends
from .database import Projects_database, PROJECT_COL
from app.PROJECTS.modals import *
from app.CORE.utility import *

#POST /projects
#POST /projects/open
#POST /projects/rename
#POST /projects/delete
#POST /projects/change
#GET /projects//user_projects

router = APIRouter(prefix="/projects")


@router.get("/user_projects") #POST
def get_user_projects(
    response: Response,
    email: str = Depends(get_current_user_email)
):
    projects = Projects_database.get_projects_by_user(email)

    current_project = None  # will hold { project_id, project_name }

    print(projects)
    project_list = []
    for project in projects:
        project_list.append({
            "project_id": project[0], #"ProjectId"
            "project_name": project[1] #"ProjectName"
        })

        if project[2] == "active": #"ProjectStatus"
            current_project = {
                "project_id": project[0], #"ProjectId"
                "project_name": project[1] #"ProjectName"
            }

    return {
        "projects": project_list,
        "current_project": current_project
    }



# -------------------------
# CREATE PROJECT
# -------------------------
@router.post("/")
def create_project_route(payload: CreateProjectRequest, response: Response, email: str = Depends(get_current_user_email)):

    # 1. Check for duplicate name
    if Projects_database.project_name_exists(email, payload.name):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Project name already exists"
        )

    # 2. Create project
    project_id = Projects_database.create_project(email, payload.name)

    # 3. Return info
    return {
        "project_id": project_id,
        "opened": payload.open_after_create
    }


# -------------------------
# OPEN PROJECT
# -------------------------
@router.post("/open")
def open_project_route(payload: OpenProjectRequest, response: Response, email: str = Depends(get_current_user_email)):


    # 1. Validate access, DELETE
    project = Projects_database.get_project_for_user(payload.project_id, email)
    if project is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found or access denied"
        )

    result = Projects_database.set_project_status(email, payload.project_id,"active")
    if result == None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="unable to open project now" # detail: Project not found or access denied
        )

    # 2. Return project info
    return {
        "project_id": project[PROJECT_COL.ProjectId],
        "project_name": project[PROJECT_COL.ProjectName]
    }


# -------------------------
# RENAME PROJECT
# -------------------------
@router.post("/rename")
def rename_project_route(payload: RenameProjectRequest, response: Response, email: str = Depends(get_current_user_email)):
    

    # 1. Ownership check, #delete
    if not Projects_database.user_is_project_owner(payload.project_id, email):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to rename this project"
        )

    # 2. Duplicate name check
    if Projects_database.project_name_exists(email, payload.new_name):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Project name already exists"
        )

    # 3. Perform rename
    success = Projects_database.rename_project(payload.project_id, payload.new_name)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to rename project"
        )

    return {"success": True, "new_name": payload.new_name}


# -------------------------
# DELETE PROJECT
# -------------------------
@router.post("/delete")
def delete_project_route(payload: DeleteProjectRequest, response: Response, email: str = Depends(get_current_user_email)):
    

    # 1. Ownership check ,Delete
    if not Projects_database.user_is_project_owner(payload.project_id, email):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to delete this project"
        )

    # 2. Get project name for confirmation
    project_name = Projects_database.get_project_name(payload.project_id)
    if project_name is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
        )

    # 3. Confirm deletion
    if payload.confirm_name != project_name:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Confirmation name does not match project name"
        )

    # 4. Perform delete
    success = Projects_database.delete_project(payload.project_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete project"
        )

    return {"success": True}


# -------------------------
# CHANGE PROJECT
# -------------------------
@router.post("/change")
def change_project_route(payload: ChangeProjectRequest, response: Response, email: str = Depends(get_current_user_email)):
    

    # 1. Validate new project access
    project = Projects_database.get_project_for_user(payload.new_project_id, email)
    if project is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="New project not found or access denied"
        )
    
    result = Projects_database.set_project_status(email, payload.new_project_id,"active")
    if result == None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="unable to open project now"
        )

    # 2. Frontend handles current project state
    return {"success": True, "current_project_id": payload.new_project_id}

