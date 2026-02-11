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
            cursor,
            model_uid,
            model_name,
            project_name,
            db_path,
            owner_email,
            "owner"
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
                    cursor,
                    owner_email,
                    model_name,
                    source_project,
                    target_project
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
            cursor,
            user_email
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
            cursor,
            user_email
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
            cursor,
            new_uid,
            new_name,
            project_name,
            new_db_path,
            owner_email,
            "owner"
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
            cursor,
            owner_email,
            current_model_name,
            new_model_name,
            model_id
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
            cursor,
            owner_email,
            model_name,
            project_name
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
            cursor,
            owner_email,
            model_name,
            source_project_name,
            target_project_name
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
        model_id, old_model_path = Models_database.get_model_id_and_path(
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

        # 3. Save file to disk
        try:
            with open(old_model_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)
        finally:
            file.file.close()


        return {
            "model_name": model_name,
            "project_name": project_name,
            "owner": owner_email,
            "created_at": datetime.now(timezone.utc).isoformat()
        }


    @staticmethod
    def BackupModel(
        *,
        cursor,
        payload: BackupModelPayload ,
        owner_email: str
    ):

        project_name = payload.current_project_name
        model_name = payload.model_name
        user_comment = payload.user_comment

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

        if not os.path.exists(model_path):
            raise HTTPException(
                status_code=404,
                detail=f"Model file does not exist on disk"
            )

        backup_id = Models_database.model_backup(
            cursor,
            model_id,
            user_comment,
            backup_path
        )

        if not backup_id:
            raise HTTPException(
                status_code=404,
                detail=f"coudnt update S_modelBackups"
            )

        backup_root = os.path.join(os.getcwd(), "BACKUP", project_name)
        os.makedirs(backup_root, exist_ok=True)

        backup_filename = f"{project_name}_{model_name}_{backup_id}.db"
        backup_path = os.path.join(backup_root, backup_filename)

        # check if file already exists at backup path, if yes reaise error
        if os.path.exists(backup_path):
            raise HTTPException(
                status_code=404,
                detail=f"Backup already exists"
            )

        shutil.copy2(model_path, backup_path)

        return {
            "message": "model backed up successfully",
            "model_name": model_name,
            "project_name": project_name,
        }

    @staticmethod
    def RestoreModel(
        *,
        cursor,
        payload: RestoreModelPayload ,
        owner_email: str
    ):
        project_name = payload.current_project_name
        model_name = payload.model_name

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

        backup_path = Models_database.get_backup_model_path(
            cursor,
            model_id,
        )

        # note :-
        #add backup_id, how do we get Backup_id, do we need to send this to user at time of /Backup ?

        if not backup_path:
            raise HTTPException(
                status_code=404,
                detail=f"Backup model not found"
            )

        if not os.path.exists(backup_path):
            raise FileNotFoundError("Backup file missing on disk")

        os.makedirs(DATA_FOLDER, exist_ok=True)

        restored_filename = os.path.basename(backup_path)
        restored_path = os.path.join(data_dir, restored_filename)

        shutil.copy2(backup_path, restored_path)

        return {
            "message": "model restored successfully",
            "project_name": payload.project_name,
            "model_name": payload.model_name
        }


    @staticmethod
    def ShareModel(
        *,
        cursor,
        payload: ShareModelPayload,
        owner_email: str
    ):
        
        fromuser_email = owner_email

        if fromuser_email == payload.touser_email:
            raise HTTPException(
                status_code=400,
                detail="You cannot share a model with yourself"
            )

        model_id, model_path = Models_database.get_model_id_and_path(
            cursor,
            payload.model_name,
            payload.project_name,
            owner_email
        )

        if not model_id:
            raise HTTPException(
                status_code=404,
                detail=(
                    f"Model '{payload.model_name}' "
                    f"not found in project '{payload.project_name}'"
                )
            )

        notification_params = {
            "model_name": payload.model_name,
            "project_name": payload.project_name,
            "access_level": payload.access_level
        }

        notification_id = Models_database.create_notification(
            cursor,
            from_user_email=fromuser_email,
            to_user_email=payload.touser_email,
            title=payload.title,
            message=payload.message,
            notification_type="MODEL_SHARE",
            notification_params={
                "model_name": payload.model_name,
                "project_name": payload.project_name,
                "access_level": payload.access_level
            }
        )

        if not notification_id:
            raise HTTPException(
                status_code=404,
                detail= "cannot send notification now."
            )

        return {
            "message": "Model shared successfully",
            "model_name": payload.model_name,
            "project_name": payload.project_name,
            "shared_with": payload.touser_email
        }


    @staticmethod
    def Get_Notifications(
        *,
        cursor,
        owner_email: str
    ):

        notifications = ModelsDatabase.get_user_notifications(
            cursor,
            owner_email
        )

        if not notifications:
            raise HTTPException(
                status_code=404,
                detail=f"No Notifications found for user: {owner_email}"
            )

        return notifications

    @staticmethod
    def is_share_model_request_accepted(
        *,
        cursor,
        owner_email: str
    ):

        # note:-
        # do i need to send notification_id with user at the time of /share, 
        # for user to fetch wether that request is accepted or not ?


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
            return row[0], row[1]
        return None, None


    @staticmethod
    def move_model_to_project2(cursor, user_email: str, model_name: str, old_project_name: str, new_project_name: str) -> int:
        old_Model_id, old_Model_path = Models_database.get_model_id_and_path(cursor, model_name, old_project_name, user_email)
        if not old_Model_id:
            return 0
        new_Model_id, new_Model_path = Models_database.get_model_id_and_path(cursor, model_name, new_project_name, user_email)
        if new_Model_id:
            return 0
        new_project_id = Models_database.get_project_id(cursor, user_email, new_project_name)
        old_project_id = Models_database.get_project_id(cursor, user_email, old_project_name)
        query = """UPDATE S_UserModels
                    SET ProjectId = ?
                    WHERE ModelId = ?
                        AND UserId = ?
                        AND ProjectId = ?
                """
        cursor.execute( query,
            (new_project_id, old_Model_id, user_email, old_project_id)
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
        
        _Model_id, _Model_path = Models_database.get_model_id_and_path(cursor, model_name, project_name, user_name)
        if _Model_id:
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
    def model_backup(
        cursor,
        *,
        model_id: int,
        backup_text: str,
        backup_path: str
    ):
        row = cursor.execute(
            """
            INSERT INTO S_ModelBackups (
                BackupText,
                ModelId,
                BackupPath
            )
            VALUES (?, ?, ?)
            RETURNING BackupId
            """,
            (backup_text, model_id, backup_path)
        ).fetchone()

        return row[0]


    @staticmethod
    def get_backup_path(
        cursor,
        model_id: int
    ):

        row = cursor.execute(
            """
            SELECT BackupPath
            FROM S_backupmodel
            WHERE ModelId = ?
            """,
            (model_id,)
        ).fetchone()

        return row[0] if row else None


    @staticmethod
    def create_notification(
        cursor,
        *,
        from_user_email: str,
        to_user_email: str,
        title: str,
        message: str,
        notification_type: str,
        notification_params: Optional[dict]
    ):

        params_text = (
            json.dumps(notification_params)
            if notification_params is not None
            else None
        )

        row = cursor.execute(
            """
            INSERT INTO S_UserNotifications (
                FromUserEmail,
                ToUserEmail,
                Title,
                Message,
                NotificationType,
                NotificationParams,
                IsRead,
                IsAccepted
            )
            VALUES (?, ?, ?, ?, ?, ?, 0,0)
            RETURNING NotificationId
            """,
            (
                from_user_email,
                to_user_email,
                title,
                message,
                notification_type,
                params_text
            )
        ).fetchone()

        return row[0]


    @staticmethod
    def get_user_notifications(
        cursor,
        user_email
    ):

        rows = cursor.execute(
            """
                SELECT Message
            FROM S_UserNotifications
            WHERE
                ToUserEmail = ?
                AND IsRead = 0
                AND IsAccepted = 0
            ORDER BY CreatedAt DESC
            """,
            (user_email,)
        ).fetchall()

        return [row["Message"] for row in rows]
