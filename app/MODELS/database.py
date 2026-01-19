from app.CORE.DB import with_master_cursor

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
            ON CONFLICT(ModelId, UserId)
            DO UPDATE SET
                ProjectId   = excluded.ProjectId,
                AccessLevel = excluded.AccessLevel,
                GrantedAt   = datetime('now')
            """,
            (model_id, user_email, project_id, access_level)
        )
    

    @staticmethod
    def get_model_id_by_name(cursor, model_name: str) -> int | None:
        """
        Fetch the ModelId for a given model_name.

        Returns:
            ModelId (int) if found, else None
        """
        row = cursor.execute(
            """
            SELECT ModelId
            FROM S_Models
            WHERE ModelName = ?
            """,
            (model_name,)
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
