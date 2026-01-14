from fastapi import HTTPException, status, APIRouter, Response, Depends
from .database import Projects_database
from app.PROJECTS.modals import *
from app.CORE.utility import *
from app.CORE.DB import with_master_cursor

router = APIRouter(prefix="/projects")


# -------------------------
# GET USER PROJECTS
# -------------------------
@router.post("/user_projects")
def get_user_projects(
    response: Response,
    email: str = Depends(get_current_user_email),
    cursor = Depends(with_master_cursor)
):
    projects = Projects_database.get_projects_by_user(cursor,email)

    current_project = None
    project_list = []

    for project in projects:
        project_name = project[0]
        project_status = project[1]

        project_list.append({
            "project_name": project_name
        })

        if project_status == "active":
            current_project = {
                "project_name": project_name
            }

    return {
        "projects": project_list,
        "current_project": current_project
    }


# -------------------------
# CREATE PROJECT
# -------------------------
@router.post("/")
def create_project_route(
    payload: CreateProjectRequest,
    response: Response,
    email: str = Depends(get_current_user_email),
    cursor = Depends(with_master_cursor)
):
    if Projects_database.project_name_exists(cursor,email, payload.name):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Project name already exists"
        )
    
    project_name = Projects_database.create_project(cursor,email, payload.name)

    if payload.open_after_create:
        r = Projects_database.set_project_status(cursor,email, project_name, "active")
        if r == None:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Unable to open project now"
            )

    return {
        "project_name": project_name,
        "opened": payload.open_after_create
    }


# -------------------------
# OPEN PROJECT
# -------------------------
@router.post("/open")
def open_project_route(
    payload: OpenProjectRequest,
    response: Response,
    email: str = Depends(get_current_user_email),
    cursor = Depends(with_master_cursor)
):

    success = Projects_database.set_project_status(
        cursor,
        email,
        payload.project_name,
        "active"
    )

    if not success:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Unable to open project now"
        )

    return {
        "project_name": payload.project_name
    }


# -------------------------
# RENAME PROJECT
# -------------------------
@router.post("/rename")
def rename_project_route(
    payload: RenameProjectRequest,
    response: Response,
    email: str = Depends(get_current_user_email),
    cursor = Depends(with_master_cursor)
):
    

    if Projects_database.project_name_exists(cursor,email, payload.new_name):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Project name already exists"
        )

    success = Projects_database.rename_project(
        cursor,
        email,
        payload.project_name,
        payload.new_name
    )

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
def delete_project_route(
    payload: DeleteProjectRequest,
    response: Response,
    email: str = Depends(get_current_user_email),
    cursor = Depends(with_master_cursor)
):

    if payload.confirm_name != payload.project_name:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Confirmation name does not match project name"
        )

    success = Projects_database.delete_project(cursor,email, payload.project_name)
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
def change_project_route(
    payload: ChangeProjectRequest,
    response: Response,
    email: str = Depends(get_current_user_email),
    cursor = Depends(with_master_cursor)
):
    project = Projects_database.get_project_for_user(cursor,email, payload.new_project_name)
    if project is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="New project not found or access denied"
        )

    success = Projects_database.set_project_status(
        cursor,
        email,
        payload.new_project_name,
        "active"
    )

    if not success:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Unable to open project now"
        )

    return {
        "success": True,
        "current_project": payload.new_project_name
    }
