from app.CORE.DB import with_master_cursor
from fastapi import HTTPException

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
            cursor.execute(
                """
                INSERT INTO S_Models (
                    ModelUID,
                    ModelName,
                    ModelPath,
                    OwnerId
                )
                VALUES (?, ?, ?, ?)
                """,
                (
                    model_uid,
                    model_name,
                    db_path,
                    owner_email
                )
            )
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
