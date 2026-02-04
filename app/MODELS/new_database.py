import sqlite3
from typing import Optional
from app.SCHEMA.schema_info import schema_info
import uuid
from app.CONFIG.config import DATA_FOLDER
import os
from fastapi import HTTPException, UploadFile,  Depends, File
from fastapi.responses import FileResponse
import shutil
from datetime import datetime, timezone
from .models import *


class Models_database:

#-------------------------- SERVICE METHODS ---------------------
    @staticmethod
    def create_model(
        *,
        cursor,
        payload: AddModelRequest,
        owner_email: str
    ) -> dict:
        """
        Handles complete model creation workflow:
        - prepare model
        - insert DB records
        - create sqlite file
        """

        model_name = payload.model_name.strip()
        model_template = payload.model_template
        project_name = payload.project_name.strip()
        upload_model_with_sample_data = payload.upload_model_with_sample_data

        # ---------- model creation logic ----------

        if model_template not in schema_info:
            raise HTTPException(status_code=400, detail="invalid model template")

        sql_file = (
            schema_info[model_template]["with_data"]
            if upload_model_with_sample_data
            else schema_info[model_template]["without_data"]
        )

        if not os.path.exists(sql_file):
            raise HTTPException(status_code=500, detail="sql template missing")

        model_uid = str(uuid.uuid4())
        db_path = os.path.join(DATA_FOLDER, f"{model_uid}.db")

        # ---------- DB insert ----------

        created = Models_database.add_user_model(
            cursor=cursor,
            model_uid=model_uid,
            model_name=model_name,
            project_name=project_name,
            db_path=db_path,
            email=owner_email,
            access_level="owner"
        )

        if not created:
            raise HTTPException(
                status_code=400,
                detail="Project not found or model could not be created"
            )

        # ----------create sqlite_db logic ----------

        try:
            with sqlite3.connect(db_path) as model_db:
                with open(sql_file, "r") as f:
                    model_db.executescript(f.read())
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

        # ---------- response ----------

        return {
            "model_name": model_name,
            "project_name": project_name,
            "owner": owner_email,
            "created_at": datetime.now(timezone.utc).isoformat()
        }


    @staticmethod
    def assign_existing_models(
        *,
        cursor,
        payload: AssignModelsRequest,
        owner_email: str
    ) -> dict:
        """
        Assign existing models from multiple projects
        into a target project for the user.
        """

        target_project = payload.target_project.strip()
        models_by_project = payload.models_by_project

        total_updated = 0

        for source_project, model_names in models_by_project.items():
            source_project = source_project.strip()

            if not source_project or not model_names:
                continue

            for model_name in model_names:
                model_name = model_name.strip()
                if not model_name:
                    continue

                updated = Models_database.move_model_to_project2(
                    cursor=cursor,
                    email=owner_email,
                    model_name=model_name,
                    source_project=source_project,
                    target_project=target_project
                )

                total_updated += updated

        if total_updated == 0:
            raise HTTPException(
                status_code=400,
                detail="No models updated"
            )

        return {
            "message": "Models assigned successfully",
            "updated_models": total_updated,
            "current_project": target_project
        }


    @staticmethod
    def get_user_models(
        *,
        cursor,
        user_email: str
    ) -> dict:
        """
        Fetch all models owned/accessible by a user.
        """

        rows = Models_database.get_models_by_email(
            cursor=cursor,
            email=user_email
        )

        if not rows:
            raise HTTPException(
                status_code=404,
                detail=f"No models found for user: {user_email}"
            )

        models = [
            {"model_name": row[0]}
            for row in rows
        ]

        return {
            "user": user_email,
            "models": models
        }

    @staticmethod
    def get_user_models_grouped_by_project(
        *,
        cursor,
        user_email: str
    ) -> dict:
        """
        Fetch user models grouped by project.
        """

        rows = Models_database.get_models_by_user_grouped(
            cursor=cursor,
            email=user_email
        )

        if not rows:
            raise HTTPException(
                status_code=404,
                detail=f"No models found for user: {user_email}"
            )

        result: dict[str, list[str]] = {}

        for project_name, model_name in rows:
            result.setdefault(project_name, []).append(model_name)

        return result


    @staticmethod
    def save_as_model(
        *,
        cursor,
        payload: SaveAsModelRequest,
        owner_email: str
    ) -> dict:
        """
        Create a new model by copying an existing model.
        """

        existing_name = payload.existing_model_name.strip()
        new_name = payload.new_model_name.strip()
        project_name = payload.project_name.strip()


        # 1. Resolve existing model + path
        model_id, model_path = Models_database.get_model_id_and_path(
            cursor,
            existing_name,
            project_name,
            owner_email
        )

        if not model_id:
            raise HTTPException(
                status_code=400,
                detail=f"model = {existing_name} does not exist"
            )

        old_db_path = model_path

        if not os.path.exists(old_db_path):
            raise HTTPException(
                status_code=500,
                detail="source db file missing"
            )

        # 2. Create new UID + DB path
        new_uid = str(uuid.uuid4())
        new_db_path = os.path.join(DATA_FOLDER, f"{new_uid}.db")

        # 3. Copy DB file
        try:
            shutil.copyfile(old_db_path, new_db_path)
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"DB copy failed, {str(e)}"
            )

        # 4. Insert new model entry
        created = Models_database.add_user_model(
            cursor=cursor,
            model_uid=new_uid,
            model_name=new_name,
            project_name=project_name,
            db_path=new_db_path,
            email=owner_email,
            access_level="owner"
        )

        if not created:
            raise HTTPException(
                status_code=500,
                detail="Model insert failed"
            )

        return {
            "message": "Model saved as new model successfully",
            "source_model": existing_name,
            "new_model": new_name,
            "project": project_name
        }


    @staticmethod
    def rename_model(
        *,
        cursor,
        payload: RenameModelRequest,
        owner_email: str
    ) -> dict:
        """
        Rename an existing model.
        """

        project_name = payload.current_project_name.strip()
        current_model_name = payload.current_model_name.strip()
        new_model_name = payload.new_model_name.strip()

        # check if model to be renamed exist or not
        model_id, model_path = Models_database.get_model_id_and_path(
            cursor,
            current_model_name,
            project_name,
            owner_email
        )
        
        if not model_id:
            raise HTTPException(
                status_code=400,
                detail="model does not exist"
            )

        # check if model with new_model_name exist or not.
        new_model_id, new_model_path = Models_database.get_model_id_and_path(
            cursor,
            new_model_name,
            project_name,
            owner_email
        )

        if new_model_id:
            raise HTTPException(
                status_code=400,
                detail="new model name must be diffrent."
            )

        updated = Models_database.rename_model_(
            cursor=cursor,
            email=owner_email,
            old_name=current_model_name,
            new_name=new_model_name,
            model_id=model_id
        )

        if not updated:
            raise HTTPException(
                status_code=400,
                detail="Model not found"
            )

        return {
            "message": "Model renamed successfully"
        }

    @staticmethod
    def delete_model(
        *,
        cursor,
        payload: DeleteModelRequest,
        owner_email: str
    ) -> dict:
        """
        Delete a model from a project.
        """

        model_name = payload.model_name.strip()
        project_name = payload.project_name.strip()

        deleted = Models_database.delete_model_(
            cursor=cursor,
            email=owner_email,
            model_name=model_name,
            project_name=project_name
        )

        if not deleted:
            raise HTTPException(
                status_code=400,
                detail="Model or project not found"
            )

        return {
            "message": "Model deleted successfully"
        }

    @staticmethod
    def move_model_to_project(
        *,
        cursor,
        payload: MoveModelToProjectRequest,
        owner_email: str
    ) -> dict:
        """
        Move a model from one project to another.
        """
        source_project_name = payload.current_project_name.strip()
        model_name = payload.model_name.strip()
        target_project_name = payload.project_name.strip()

        updated = Models_database.move_model_to_project2(
            cursor=cursor,
            email=owner_email,
            model_name=model_name,
            old_project_name=source_project_name,
            new_project_name=target_project_name
        )

        if not updated:
            raise HTTPException(
                status_code=400,
                detail="Model or project not found"
            )

        return {
            "message": "Model moved to project successfully"
        }

    @staticmethod
    def download_model(
        *,
        cursor,
        payload: DownloadModelRequest,
        owner_email: str
    ):
        """
        Download a model file for a given project.
        Returns FileResponse directly.
        """

        model_name = payload.model_name.strip()
        project_name = payload.project_name.strip()

        # 1. check duplicate
        model_id, model_path = Models_database.get_model_id_and_path(
            cursor,
            model_name,
            project_name,
            owner_email
        )

        if not model_id:
            raise HTTPException(
                status_code=404,
                detail=f"Model '{model_name}' not found in project '{project_name}'"
            )

        # 2. Filesystem validation
        if not os.path.exists(model_path):
            raise HTTPException(
                status_code=404,
                detail=f"Model file not found on server at {model_path}"
            )

        # 3. Return file
        return FileResponse(
            path=model_path,
            filename=f"{model_name}.db",
            media_type="application/octet-stream"
        )

    @staticmethod
    def upload_model(
        *,
        cursor,
        payload: UploadModelPayload = Depends(upload_payload),
        file: UploadFile = File(...),
        owner_email: str
    ) -> dict:
        """
        Upload a .db model file and register it under a project.
        """

        model_name = payload.model_name.strip()
        project_name = payload.project_name.strip()

        # 1. File validation
        if not file.filename or not file.filename.lower().endswith(".db"):
            raise HTTPException(
                status_code=400,
                detail="Only .db files are allowed"
            )


        # 2. Duplicate model check
        model_id, model_path = Models_database.get_model_id_and_path(
            cursor,
            model_name,
            project_name,
            owner_email,
        )

        if not model_id:
            raise HTTPException(
                status_code=400,
                detail=f"Model '{model_name}' or '{project_name} does not exist.'"
            )

        # 3. Generate UID + path
        new_model_uid = str(uuid.uuid4())
        new_db_path = os.path.join(DATA_FOLDER, f"{new_model_uid}.db")

        # 4. Save file to disk
        try:
            with open(new_db_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)
        finally:
            file.file.close()

        # 5. Insert DB record
        try:
            # ?
            Models_database.update_model_by_id(
                cursor,
                model_id,
                new_model_uid,
                new_db_path,
                owner_email

            )
        except Exception:
            # rollback filesystem side-effect
            if os.path.exists(new_db_path):
                os.remove(new_db_path)

            raise HTTPException(
                status_code=409,
                detail="Model already exists"
            )

        return {
            "model_name": model_name,
            "project_name": project_name,
            "owner": owner_email,
            "created_at": datetime.now(timezone.utc).isoformat()
        }


# -----------------------   DATABASE METHODS  ----------------------
    
    @staticmethod
    def get_models_by_email(cursor, email):
        result = cursor.execute(
            """
            SELECT m.ModelName
            FROM S_Models m
            JOIN S_UserModels um ON um.ModelId = m.ModelId
            WHERE um.UserId=?
            """,
            (email,)
        ).fetchall()
        return result 

    @staticmethod
    def get_models_by_user_grouped(cursor, email):
        result = cursor.execute(
            """
            SELECT p.ProjectName, m.ModelName
            FROM S_UserModels um
            JOIN S_Projects p ON p.ProjectId = um.ProjectId
            JOIN S_Models m ON m.ModelId = um.ModelId
            WHERE um.UserId=?
            ORDER BY p.ProjectName
            """,
            (email,)
        ).fetchall()
        return result

    
    @staticmethod
    def rename_model_(cursor, email, old_name, new_name, model_id) -> int:
        result = cursor.execute(
            """
            UPDATE S_Models
            SET ModelName=?
            WHERE ModelName=? AND OwnerId=? AND ModelId = ?
            """,
            (new_name, old_name, email, model_id)
        ).fetchone()
        return result

    @staticmethod
    def delete_model_(cursor, email, model_name, project_name) -> int:
        project_id =Models_database.get_project_id(cursor, email, project_name)

        if not project_id:
            return 0
    
        model_id, Model_path = Models_database.get_model_id_and_path(
            cursor,
            model_name,
            project_name,
            email
        )

        if not model_id:
            return 0
        
        cursor.execute(
            """
            DELETE FROM S_UserModels
            WHERE UserId=? AND ProjectId=? AND ModelId= ?
            """,
            (email, project_id, model_id)
        )

        still_used = cursor.execute(
            "SELECT 1 FROM S_UserModels WHERE ModelId = ? LIMIT 1",
            (model_id,)
        ).fetchone()
    
        if still_used:
            return 1

        cursor.execute(
            "DELETE FROM S_Models WHERE ModelId = ? AND OwnerId = ?",
            (model_id, email)
        )

        return 1


    @staticmethod
    def get_model_id_and_path(cursor, model_name: str,
                            project_name: str,
                            user_name: str):
        query = """select S_Models.ModelId, S_Models.ModelPath
                    from S_UserModels, S_Projects, S_Models
                    WHERE S_UserModels.UserId = S_Projects.UserEmail
                    AND   S_UserModels.ProjectId = S_Projects.ProjectId
                    AND   S_UserModels.ModelId = S_Models.ModelId
                    AND   S_Projects.ProjectName = ?
                    AND   S_Models.ModelName = ?
                    AND   S_UserModels.UserId = ?"""
        row = cursor.execute(query, (project_name, model_name, user_name)).fetchone()
        if row:
            return {
                "ModelId": row[0],
                "ModelPath": row[1]
            }
        return False


    @staticmethod
    def move_model_to_project2(cursor, user_email: str, model_name: str, old_project_name: str, new_project_name: str) -> int:
        old_record = Models_database.get_model_id_and_path(cursor, model_name, old_project_name, user_email)
        if not old_record:
            return 0
        new_record = Models_database.get_model_id_and_path(cursor, model_name, new_project_name, user_email)
        if new_record:
            return 0
        model_id, model_path = old_record["ModelId"], old_record["ModelPath"]
        new_project_id = Models_database.get_project_id(cursor, user_email, new_project_name)
        old_project_id = Models_database.get_project_id(cursor, user_email, old_project_name)
        query = """UPDATE S_UserModels
                    SET ProjectId = ?
                    WHERE ModelId = ?
                        AND UserId = ?
                        AND ProjectId = ?
                """
        cursor.execute( query,
            (new_project_id, model_id, user_email, old_project_id)
        )                


    @staticmethod
    def add_user_model(
        cursor,
        model_uid: str,
        model_name: str,
        project_name: str,
        db_path: str,
        user_name: str,
        role: str = "owner"
    ):
        
        project_id = Models_database.get_project_id(cursor, user_name, project_name)
        if not project_id:
            raise Exception("Project does not exist for user")
        
        record = Models_database.get_model_id_and_path(cursor, model_name, project_name, user_name)
        if record:
            raise Exception("Model already exists in project for user")
        
        model_id = cursor.execute(
            """
            INSERT INTO S_Models (
                ModelUID,
                ModelName,
                ModelPath,
                OwnerId
            )
            VALUES (?, ?, ?, ?)
            RETURNING ModelId
            """,
            (
                model_uid,
                model_name,
                db_path,
                user_name
            )
        ).fetchone()[0]

        cursor.execute(
            """
            INSERT INTO S_UserModels (
                ModelId,
                UserId,
                ProjectId,
                AccessLevel,
                GrantedAt
            )
            VALUES (?, ?, ?, ?, datetime('now'))
            """,
            (model_id, user_name, project_id, role)
        )

        return True
    

    @staticmethod
    def get_project_id(cursor, email: str, project_name: str) -> Optional[int]:
        row = cursor.execute(
            """
            SELECT p.ProjectId
            FROM S_Projects p
            WHERE p.UserEmail=? AND p.ProjectName=?
            """,
            (email, project_name)
        ).fetchone()
        return row[0] if row else None


    @staticmethod
    def update_model_by_id(cursor, model_id, new_model_uid, new_model_path, owner_email):

        row = cursor.execute(
            """
            UPDATE S_Models
            SET ModelUID = ?,
                ModelPath = ?
            WHERE ModelId = ?
              AND OwnerId = ?
            """,
            (new_model_uid, new_model_path, model_id, owner_email)
        ).fetchone()

        return row
