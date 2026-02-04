from numpy import record
from app.CORE.DB import with_master_cursor
from fastapi import HTTPException
from app.PROJECTS.database import Projects_database

class S_MODELS_COL:
    ModelId     = 0
    ModelUID    = 1
    ModelName   = 2
    ProjectName = 3
    ModelPath   = 4
    CreatedAt   = 5
    OwnerId     = 6

class S_USERMODELS_COL:
    ModelId     = 0
    UserId      = 1
    AccessLevel = 2
    GrantedAt   = 3


class Models_database:

    # added 20-JAN-2026
    @staticmethod
    def get_models_by_user_grouped(cursor, user_email: str):
        query = """
            SELECT
                p.ProjectName,
                m.ModelName
            FROM S_UserModels um
            JOIN S_Models m
                ON um.ModelId = m.ModelId
            JOIN S_Projects p
                ON um.ProjectId = p.ProjectId
            WHERE um.UserId = ?
            ORDER BY p.ProjectName, m.ModelName
        """
        row = cursor.execute(query, (user_email,)).fetchall()
        return row


    # added 20-JAN-2026
    @staticmethod
    def assign_project_to_models2(cursor, user_email: str, model_dict: dict, new_project_name: str):
        for old_project_name in model_dict:
            model_names = model_dict[old_project_name]
            for model_name in model_names:
                Models_database.move_model_to_project2(cursor, user_email, model_name, old_project_name, new_project_name)


    @staticmethod
    def assign_project_to_models(cursor, user_email: str, model_names: list[str], project_name: str):
        """
        Assigns the given project's ProjectId to the specified user's models.
        Supports multiple model names at once.
        Returns number of rows updated.
        """
        if not model_names:
            return 0  # nothing to update

        # Create placeholders for parameterized query, e.g. (?, ?, ?) if 3 model names
        placeholders = ','.join('?' for _ in model_names)

        query = f"""
        UPDATE S_UserModels
        SET ProjectId = S_Projects.ProjectId
        FROM S_Projects, S_Models
        WHERE S_Projects.UserEmail = S_UserModels.UserId
          AND S_Projects.ProjectName = ?
          AND S_Projects.UserEmail = ?
          AND S_UserModels.ModelId = S_Models.ModelId
          AND S_Models.ModelName IN ({placeholders})
        """

        # Parameters: project_name, user_email, then all model names
        params = [project_name, user_email] + model_names
        result = cursor.execute(query, params).fetchall()
        return result


    @staticmethod
    def get_models_by_email(cursor, user_email: str):
        """
        Fetch all models for a given user email, ordered by CreatedAt DESC.

        Returns list of rows: each row has ModelName, ModelUID, etc.
        """
        rows = cursor.execute(
            """
            SELECT ModelName, ModelUID, ModelPath, CreatedAt, OwnerId
            FROM S_Models
            WHERE OwnerId = ?
            ORDER BY CreatedAt DESC
            """,
            (user_email,)
        ).fetchall()

        return rows


    @staticmethod
    def assign_model_to_user(
        cursor,
        model_id: int,
        user_email: str,
        project_id: int,
        access_level: str = "owner"
    ):
        """
        Assign or update a model for a user.
        If already exists, replace ProjectId and AccessLevel.
        """
    
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
            ON CONFLICT (ModelId, UserId, ProjectId)
            DO UPDATE SET
                ProjectId   = excluded.ProjectId,
                AccessLevel = excluded.AccessLevel,
                GrantedAt   = datetime('now')
            """,
            (model_id, user_email, project_id, access_level)
        )
    

    @staticmethod
    def get_model_id_by_name(
        cursor,
        model_name: str,
        model_uid: str
    ):
        """
        Fetch the ModelId for a given model_name and model_uid.
        """

        row = cursor.execute(
            """
            SELECT ModelId
            FROM S_Models
            WHERE ModelName = ?
              AND ModelUID  = ?
            """,
            (model_name, model_uid)
        ).fetchone()

        if row:
            return row[0]
        return None
    
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
    def add_user_model(
        cursor,
        model_uid: str,
        model_name: str,
        project_name: str,
        db_path: str,
        user_name: str,
        role: str = "owner"
    ):
        
        project_id = Projects_database.get_project_id_for_user(cursor, user_name, project_name)
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
    def add_model(
        cursor,
        model_uid: str,
        model_name: str,
        db_path: str,
        owner_email: str
    ):
        """
        Insert a new model into S_Models.
        Raises exception if model already exists (UNIQUE constraint).
        """
        try:
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
                        owner_email
                    )
                ).fetchone()[0]
            print("Model added with ModelId:", model_id)
            return True
        except Exception as e:
            print("Exception occured in, add_model", str(e))
            return False

    @staticmethod
    def insert_user_model(
        cursor,
        model_id: int,
        user_id: str,
        project_id: int
    ):
        """
        Insert a new row into S_UserModels.
        Fails if (ModelId, UserId) already exists.
        """
    
        cursor.execute(
            """
            INSERT INTO S_UserModels (
                ModelId,
                UserId,
                ProjectId,
                AccessLevel,
                GrantedAt
            )
            VALUES (?, ?, ?, 'owner', datetime('now'))
            """,
            (model_id, user_id, project_id)
        )


    @staticmethod
    def model_exists_in_project(cursor, project_id: int, model_name: str) -> bool:
        """
        Check if a model with the given name already exists in the given project.
        Returns True if exists, False otherwise.
        """
        row = cursor.execute("""
            SELECT 1
            FROM S_UserModels um
            JOIN S_Models m ON um.ModelId = m.ModelId
            WHERE um.ProjectId = ? AND m.ModelName = ?
            LIMIT 1
        """, (project_id, model_name)).fetchone()
        
        return row is not None


    @staticmethod
    def get_model_with_project_id_by_name(cursor, email, model_name, project_id):
        rows = cursor.execute(
            """
            SELECT
                m.ModelUID,
                m.ModelPath,
                um.ProjectId
            FROM S_Models m
            JOIN S_UserModels um ON um.ModelId = m.ModelId
            WHERE um.UserId = ?
              AND m.ModelName = ?
              AND um.ProjectId = ?
            LIMIT 1
            """,
            (email, model_name, project_id)
        ).fetchone()


        if not rows:
            return None

        if len(rows) > 1:
            raise HTTPException(
                400,
                f"Model '{model_name}' exists in multiple projects"
            )

        r = rows[0]
        return {
            "ModelUID": r[0],
            "ModelPath": r[1],
            "ProjectId": r[2],
        }


    @staticmethod
    def get_model_by_name_and_project(cursor, email, model_name, project_id):
        row = cursor.execute(
            """
            SELECT
                m.ModelId,
                m.ModelUID,
                m.ModelPath
            FROM S_Models m
            JOIN S_UserModels um ON um.ModelId = m.ModelId
            WHERE um.UserId = ?
              AND um.ProjectId = ?
              AND m.ModelName = ?
            """,
            (email, project_id, model_name)
        ).fetchone()
    
        if not row:
            return None
    
        return {
            "ModelId": row[0],
            "ModelUID": row[1],
            "ModelPath": row[2]
        }



    @staticmethod
    def rename_model(cursor, user_email: str, current_name: str, new_name: str) -> int:
        result = cursor.execute(
            """
            UPDATE S_Models
            SET ModelName = ?
            WHERE ModelName = ?
              AND OwnerId = ?
            """,
            (new_name, current_name, user_email)
        ).fetchone()
        return result

    @staticmethod
    def delete_model(cursor, user_email: str, model_name: str, project_name: str) -> int:

        # use get_model_id_and_path

        # also check if owner, delete from S_Models and user, else only delete from S_UserModels
         # if deleted from S_Models then delete file also

    
        row = cursor.execute(
            """
            SELECT m.ModelId, p.ProjectId
            FROM S_Models m, S_UserModels um, S_Projects p
            WHERE m.ModelId = um.ModelId
              AND um.ProjectId = p.ProjectId
              AND p.UserEmail   = um.UserId
            WHERE m.ModelName   = ?
              AND p.ProjectName = ?
              AND p.UserEmail   = ?
              AND um.UserId     = ?
            """,
            (model_name, project_name, user_email, user_email)
        ).fetchone()
    
        if not row:
            return 0
    
        model_id, project_id = row
    
        cursor.execute(
            """
            DELETE FROM S_UserModels
            WHERE ModelId = ?
              AND ProjectId = ?
              AND UserId = ?
            """,
            (model_id, project_id, user_email)
        )
    
        deleted = cursor.execute("SELECT changes()").fetchone()[0]
    
        if deleted == 0:
            return 0
    
        still_used = cursor.execute(
            "SELECT 1 FROM S_UserModels WHERE ModelId = ? LIMIT 1",
            (model_id,)
        ).fetchone()
    
        if still_used:
            return 1
    
        cursor.execute(
            "DELETE FROM S_Models WHERE ModelId = ? AND OwnerId = ?",
            (model_id, user_email)
        )
    
        return 1

    @staticmethod
    def move_model_to_project2(cursor, user_email: str, model_name: str, old_project_name: str, new_project_name: str) -> int:
        old_record = Models_database.get_model_id_and_path(cursor, model_name, old_project_name, user_email)
        if not old_record:
            return 0
        new_record = Models_database.get_model_id_and_path(cursor, model_name, new_project_name, user_email)
        if new_record:
            return 0
        model_id, model_path = old_record["ModelId"], old_record["ModelPath"]
        new_project_id = Projects_database.get_project_id_for_user(cursor, user_email, new_project_name)
        old_project_id = Projects_database.get_project_id_for_user(cursor, user_email, old_project_name)
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
    def move_model_to_project(cursor, user_email: str, model_name: str, project_name: str) -> int:
        model = cursor.execute(
            """
            SELECT ModelId FROM S_Models
            WHERE ModelName = ? AND OwnerId = ?
            """,
            (model_name, user_email)
        ).fetchone()

        if not model:
            return 0

        project = cursor.execute(
            """
            SELECT ProjectId FROM S_Projects
            WHERE ProjectName = ? AND UserEmail = ?
            """,
            (project_name, user_email)
        ).fetchone()

        if not project:
            return 0

        result = cursor.execute(
            """
            UPDATE S_UserModels
            SET ProjectId = ?
            WHERE ModelId = ?
              AND UserId = ?
            """,
            (project[0], model[0], user_email)
        ).fetchone()

        return result
