import sqlite3
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
import json

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

                total_updated += updated or 0

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

        result: dict[str, dict[str, str]] = {}

        for project_name, model_name, access_level in rows:
            result.setdefault(project_name, {})[model_name] = access_level

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

        existing_name = payload.model_name.strip()
        new_name = payload.new_model_name.strip()
        project_name = payload.project_name.strip()
        Save_as_From_User_Email = payload.Save_as_From_User_Email.strip()

        is_user_email = Models_database.valid_email(Save_as_From_User_Email)

        # 1. Resolve existing model + path
        model_id, model_path = Models_database.get_model_id_and_path(
            cursor,
            existing_name,
            project_name,
            #owner_email
            Save_as_From_User_Email if is_user_email else owner_email
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
            "USER" if is_user_email else "owner"
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

        project_name = payload.project_name.strip()
        current_model_name = payload.model_name.strip()
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

        project_name = payload.project_name
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

        #############
       
        access_level = Models_database.get_user_access_level(
            cursor,
            model_id,
            owner_email
        )

        if access_level != "owner":
            raise HTTPException(
                status_code=404,
                detail=f"you are not owner of this {model_name}, so you cannot Backup it."
            )
        ##############

        if not os.path.exists(model_path):
            raise HTTPException(
                status_code=404,
                detail=f"Model file does not exist on disk"
            )

        # take count of no of backups of that model_id, max 10 backups of that model.
        count = Models_database.get_backup_count_by_model(cursor, model_id) #added

        backup_no = 0
        if count >= 10:
            backup_no  = 1
        else:
            backup_no = count + 1

        backup_root = os.path.join(os.getcwd(), "BACKUP")
        os.makedirs(backup_root, exist_ok=True)

        backup_filename = f"{project_name}_{model_name}_{backup_no}.db"
        backup_path = os.path.join(backup_root, backup_filename)
        
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
        payload: RestoreModelPayload , # add Backup_id - DONE
        owner_email: str
    ):
        project_name = payload.project_name
        model_name = payload.model_name
        backup_id = payload.Backup_id

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

        ############
        
        access_level = Models_database.get_user_access_level(
            cursor,
            model_id,
            owner_email
        )
        
        if access_level != "owner":
            raise HTTPException(
                status_code=404,
                detail=f"you are not owner of this {model_name}, so you cannot Restore it."
            )
        ###################

        backup_path = Models_database.get_backup_path(
            cursor,
            model_id,
            backup_id
        )


        if not backup_path:
            raise HTTPException(
                status_code=404,
                detail=f"Backup model not found"
            )

        if not os.path.exists(backup_path):
            raise FileNotFoundError("Backup file missing on disk")

        os.makedirs(DATA_FOLDER, exist_ok=True)

        restored_filename = os.path.basename(backup_path)
        restored_path = os.path.join(DATA_FOLDER, restored_filename)

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

        ##############
        access_level = Models_database.get_user_access_level(
            cursor,
            model_id,
            owner_email
        )

        if access_level != "owner":
            raise HTTPException(
                status_code=404,
                detail=f"you are not owner of this {payload.model_name}, so you cannot Share it."
            )
        ################

        notification_params = {
            "model_name": payload.model_name,
            "project_name": payload.project_name,
            "access_level": payload.access_level
        }

        notification_id = Models_database.create_notification(
            cursor,
            from_user_email=fromuser_email,
            to_user_email=payload.touser_email,
            title=f"this user {fromuser_email} Shared Model = {payload.model_name} With You",   #updated
            message=f"this user {fromuser_email} Shared Model = {payload.model_name} With You",
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

        notifications = Models_database.get_user_notifications(
            cursor,
            owner_email
        )

        if not notifications:
            raise HTTPException(
                status_code=404,
                detail=f"No Notifications found for user: {owner_email}"
            )

        return notifications # add NotificationId - Done


    @staticmethod
    def is_share_model_request_accepted(
        *,
        cursor,
        payload: IsAcceptedModelPayload,
        owner_email: str
    ):
        
        notification_id = payload.notification_id
        project_name = payload.project_name
        model_name = payload.model_name
        current_project = payload.new_project
        From_user_email = payload.From_user_email

        # check if model already exist for new user
        model_id, model_path = Models_database.get_model_id_and_path(
            cursor,
            model_name,
            project_name,
            owner_email
        )

        if model_id:
            raise HTTPException(
                status_code=404,
                detail=f"Model '{model_name}' already exist for user in project '{project_name}'"
            )
        
        # get model_id from from_user
        new_model_id, new_model_path = Models_database.get_model_id_and_path(
            cursor,
            model_name,
            project_name,
            From_user_email
        )

        #get project id of current active project of user
        project_id = Models_database.get_project_id(cursor, owner_email, current_project)

        # add refference to s_usermodels
        updated = Models_database.accept_model(
            cursor,
            new_model_id,
            project_id,
            owner_email,
            model_name
        )

        row = Models_database.share_model_request_accepted(
            cursor,
            notification_id,
            owner_email,
            "1",
            "1"
        )

        if not row:
            raise HTTPException(
                status_code=404,
                detail="Notification not found or already accepted"
            )

        return {
            "message": "Request accepted successfully",
            "notification_id": row[0]
        }


    @staticmethod
    def get_model_backups(
        *,
        cursor,
        payload: ModelBackupPayload,
        owner_email: str
    ):

        model_id, model_path = Models_database.get_model_id_and_path(
            cursor,
            payload.model_name,
            payload.project_name,
            owner_email
        )

        if not model_id:
            raise HTTPException(
                status_code=400,
                detail="model_id is required"
            )

        backups = Models_database.FetchModelBackups(
            cursor, 
            model_id
        )

        if not backups:
            raise HTTPException(
                status_code=400,
                detail=f"no backups found for {payload.model_name} and {payload.project_name}"
            )
    
        return backups

    @staticmethod
    def get_all_user_emails(
        cursor,
        current_user_email: str 
    ):
        
        emails =  Models_database.fetch_user_emails(
            cursor,
            current_user_email
        )

        if not emails:
            raise HTTPException(
                status_code=400,
                detail="no users found"
            )

        return emails


    @staticmethod
    def Reject_Request_For_Model_Share(
        *,
        cursor,
        payload: RejectModelSharePayload,
        current_user_email: str 
    ):

        notification_id = payload.notification_id

        row = Models_database.share_model_request_accepted(
            cursor,
            notification_id,
            current_user_email,
            "1",
            "-1"
        )

        if not row:
            raise HTTPException(
                status_code=404,
                detail="Notification not found or already accepted"
            )

        return {
            "message": "Request Rejected successfully",
            "notification_id": row[0]
        }
    
    
    #added
    @staticmethod
    def Cancel_Request_For_Model_Share(
        *,
        cursor,
        payload: CancelModelSharePayload,
        current_user_email: str 
    ):

        notification_id = payload.notification_id

        row = Models_database.share_model_request_accepted(
            cursor,
            notification_id,
            current_user_email,
            "1",
            "0"
        )

        if not row:
            raise HTTPException(
                status_code=404,
                detail="Notification not found or already accepted"
            )

        return {
            "message": "Request Canceled successfully",
            "notification_id": row[0]
        }

    @staticmethod
    def valid_email(v):
        return isinstance(v, str) and "@" in v and "." in v


# -----------------------   DATABASE METHODS  ----------------------
    
    @staticmethod
    def get_models_by_email(cursor, email):
        result = cursor.execute(
            """
            SELECT ModelId, ModelName
            FROM S_UserModels
            WHERE UserId = ?
            """,
            (email,)
        ).fetchall()
        return result 

    @staticmethod
    def get_models_by_user_grouped(cursor, email):
        result = cursor.execute(
            """
            SELECT
                p.ProjectName,
                um.ModelName,
                um.AccessLevel
            FROM S_UserModels um
            JOIN S_Projects p ON p.ProjectId = um.ProjectId
            WHERE um.UserId = ?
            ORDER BY p.ProjectName
            """,
            (email,)
        ).fetchall()
        return result

    #change - DONE, look for betterment
    @staticmethod
    def rename_model_(cursor, email, old_name, new_name, model_id) -> int:
        result = cursor.execute(
            """
            UPDATE S_UserModels
            SET ModelName = ?
            WHERE ModelId  = ?
              AND UserId   = ?
              AND ModelName = ?
            RETURNING ModelId
            """,
            (new_name, model_id, email, old_name)
        ).fetchone()
        return result

    @staticmethod
    def delete_model_(cursor, email, model_name, project_name) -> int:
        
    
        model_id, Model_path = Models_database.get_model_id_and_path(
            cursor,
            model_name,
            project_name,
            email
        )

        if not model_id:
            return 0

        access_level = cursor.execute(
            """
            DELETE FROM S_UserModels
            WHERE UserId=? AND ModelId= ?
            RETURNING AccessLevel
            """,
            (email, model_id)
        ).fetchone()[0]


        if access_level != "owner":
            return 1

        #delete from s_moddels
        cursor.execute(
            "DELETE FROM S_Models WHERE ModelId = ?",
            (model_id,)
        )
        
        #delete all its referrences from s_usermodels
        cursor.execute(
            "DELETE FROM S_UserModels WHERE ModelId = ?",
            (model_id,)
        )

        #fetch all backuppaths of model_id
        paths = cursor.execute(
                    " SELECT BackupPath FROM S_ModelBackups WHERE ModelId = ?",
                    (model_id,)
                ).fetchall()

        #delete all its backups
        cursor.execute(
            "DELETE FROM S_ModelBackups WHERE ModelId = ?",
            (model_id,)
        )

        #delete all backup files of model_id
        for (path,) in paths:
            if path and os.path.exists(path):
                os.remove(path)

        #delete .db file as well, here.
        if os.path.exists(Model_path):
            os.remove(Model_path)
            print("file deleted")

        return 1

    #change - DONE
    @staticmethod
    def get_model_id_and_path(cursor, model_name: str,
                            project_name: str,
                            user_name: str):
        query = """SELECT S_Models.ModelId, S_Models.ModelPath
                FROM S_UserModels, S_Projects, S_Models
                WHERE S_UserModels.ProjectId = S_Projects.ProjectId
                  AND S_UserModels.ModelId  = S_Models.ModelId
                  AND S_Projects.UserEmail  = S_UserModels.UserId
                  AND S_Projects.ProjectName = ?
                  AND S_UserModels.ModelName = ?
                  AND S_UserModels.UserId    = ?
                LIMIT 1"""
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
                    RETURNING ModelId
                """
        row = cursor.execute( query,
            (new_project_id, old_Model_id, user_email, old_project_id)
        ).fetchone()  

        return 1 if row else 0              

    #change - DONE, Check for errors
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
                ModelPath,
                OwnerId
            )
            VALUES (?, ?, ?)
            RETURNING ModelId
            """,
            (
                model_uid,
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
                ModelName,
                GrantedAt
            )
            VALUES (?, ?, ?, ?, ?, datetime('now'))
            """,
            (model_id, user_name, project_id, role, model_name)
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
        model_id: int,
        backup_text: str,
        backup_path: str
    ):
        cursor.execute(
            """
                DELETE FROM S_ModelBackups
                WHERE BackupPath = ?
            """,
            (backup_path,)
        )

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
        model_id: int,
        backup_id: str
    ):

        row = cursor.execute(
            """
            SELECT BackupPath
            FROM S_ModelBackups
            WHERE ModelId = ?
            AND BackupId = ?
            """,
            (model_id, backup_id)
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
               SELECT
                NotificationId,
                Message,
                FromUserEmail,
                json_extract(NotificationParams, '$.project_name') AS ProjectName,
                json_extract(NotificationParams, '$.model_name') AS ModelName,
                IsRead,
                IsAccepted
            FROM S_UserNotifications
            WHERE
                ToUserEmail = ?
                AND (IsRead = 0 OR IsAccepted = 0)
            ORDER BY CreatedAt DESC

            """,
            (user_email,)
        ).fetchall()


        return {
            row[0]: {
                "message": row[1],
                "from_user": row[2],
                "project_name": row[3],
                "model_name": row[4],
                "Is_Read": row[5],  #updated
                "Is_Accepted": row[6]
            }
            for row in rows
        }



    @staticmethod
    def FetchModelBackups(
        cursor,
        model_id: int
    ):

        rows = cursor.execute(
            """
            SELECT BackupId, BackupText, CreatedAt
            FROM S_ModelBackups
            WHERE ModelId = ?
            ORDER BY CreatedAt DESC
            """,
            (model_id,)
        ).fetchall()

        if not rows:
            return {
                "message": "No backups found for this model",
                "backups": []
            }

        return {
            "model_id": model_id,
            "backups": [
                {
                    "backup_id": row[0],
                    "backup_text": row[1],
                    "backup_date": row[2]
                }
                for row in rows
            ]
        }

    @staticmethod
    def fetch_user_emails(cursor, current_user_email: str):

        rows = cursor.execute(
            """
            SELECT UserEmail
            FROM S_Users
            WHERE UserEmail != ?
            """,
            (current_user_email,)
        ).fetchall()

        return [row[0] for row in rows]


    @staticmethod
    def share_model_request_accepted(cursor, notification_id, email, IsRead, IsAccepted):
        row = cursor.execute(
            """
            UPDATE S_UserNotifications
            SET
                IsAccepted = ?,
                IsRead = ?,
                ReadAt = datetime('now')
            WHERE NotificationId = ?
            AND ToUserEmail = ?
            AND IsAccepted = 0
            RETURNING NotificationId
            """,
            (IsAccepted, IsRead, notification_id, email)
        ).fetchone()

        return row


    @staticmethod
    def accept_model(cursor, model_id, project_id, new_email, model_name):
        row = cursor.execute(
            """
            INSERT INTO S_UserModels (
                ModelId,
                UserId,
                ProjectId,
                AccessLevel,
                ModelName
            )
            VALUES (?, ?, ?, 'USER', ?)
            RETURNING ModelId;
            """,
            (model_id, new_email, project_id, model_name)
        ).fetchone()

        return row


    @staticmethod
    def get_user_access_level(cursor, model_id, user_email):
        row = cursor.execute(
            """
            SELECT AccessLevel
            FROM S_UserModels
            WHERE ModelId = ?
              AND UserId = ?
            """,
            (model_id, user_email)
        ).fetchone()

        return row[0] if row else None

    @staticmethod
    def get_backup_count_by_model(cursor, model_id):
        row = cursor.execute(
            """
            SELECT COUNT(*) 
            FROM S_ModelBackups
            WHERE ModelId = ?
            """,
            (model_id,)
        ).fetchone()

        return row[0] if row else 0