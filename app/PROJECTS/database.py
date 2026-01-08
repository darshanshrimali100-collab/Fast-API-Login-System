import sqlite3
from app.CONFIG.config import DB_PATH


class PROJECT_COL:
    ProjectId = 0
    UserEmail = 1
    ProjectName = 2
    ProjectStatus = 3
    CreatedAt = 4
    UpdatedAt = 5


class Projects_database:

    __Db_is_connected = None

    @classmethod
    def connect(cls):
        cls.__Db_is_connected = sqlite3.connect(DB_PATH, check_same_thread=False)
        cls.__Db_is_connected.row_factory = sqlite3.Row
        return cls.__Db_is_connected

    @staticmethod
    def get_active_projects_by_email(user_email: str):
        if Projects_database.__Db_is_connected is None:
            return {"message": "db is not connected"}
    
        conn = Projects_database.__Db_is_connected
        cursor = conn.cursor()
    
        cursor.execute(
            """
            SELECT
                ProjectId,
                ProjectName,
                ProjectStatus,
                CreatedAt,
                UpdatedAt
            FROM S_Projects
            WHERE UserEmail = ?
              AND ProjectStatus = 'active'
            ORDER BY UpdatedAt DESC
            """,
            (user_email,)
        )
    
        return cursor.fetchall()

    @staticmethod
    def set_project_status(user_email: str, project_id: str, status: str):
        """
        Update the status of a project for a given user.

        Args:
            user_email (str): The user's email.
            project_name (str): The project name.
            status (str): The new status (e.g., "active", "inactive").

        Returns:
            bool: True if a project was updated, False otherwise.
        """
        if Projects_database.__Db_is_connected is None:
            return {"message": "db is not connected"}

        cursor = Projects_database.__Db_is_connected.cursor()

        cursor.execute(
            """
            UPDATE S_Projects
            SET ProjectStatus = NULL
            WHERE UserEmail = ?
            """,
            (user_email,)
        )

        cursor.execute(
            """
            UPDATE S_Projects
            SET ProjectStatus = ?, UpdatedAt = datetime('now')
            WHERE UserEmail = ? AND Projectid = ?
            """,
            (status, user_email, project_id)
        )
        Projects_database.__Db_is_connected.commit()
        return cursor.rowcount > 0


    @staticmethod
    def create_project(user_email: str, project_name: str):
        if Projects_database.__Db_is_connected is None:
            return {"message": "db is not connected"}

        conn = Projects_database.__Db_is_connected
        cursor = conn.cursor()

        cursor.execute(
            """
            INSERT INTO S_Projects (
                UserEmail,
                ProjectName,
                CreatedAt,
                UpdatedAt
            )
            VALUES (?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            """,
            (user_email, project_name)
        )

        conn.commit()
        return cursor.lastrowid

    @staticmethod
    def project_name_exists(user_email: str, project_name: str):
        if Projects_database.__Db_is_connected is None:
            return {"message": "db is not connected"}

        conn = Projects_database.__Db_is_connected
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT 1
            FROM S_Projects
            WHERE UserEmail = ?
              AND ProjectName = ?
            LIMIT 1
            """,
            (user_email, project_name)
        )

        return cursor.fetchone() is not None

    @staticmethod
    def get_project_by_id(project_id: int):
        if Projects_database.__Db_is_connected is None:
            return {"message": "db is not connected"}

        conn = Projects_database.__Db_is_connected
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT *
            FROM S_Projects
            WHERE ProjectId = ?
            LIMIT 1
            """,
            (project_id,)
        )

        return cursor.fetchone()

    @staticmethod
    def get_project_for_user(project_id: int, user_email: str):
        if Projects_database.__Db_is_connected is None:
            return {"message": "db is not connected"}

        conn = Projects_database.__Db_is_connected
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT *
            FROM S_Projects
            WHERE ProjectId = ?
              AND UserEmail = ?
            LIMIT 1
            """,
            (project_id, user_email)
        )

        return cursor.fetchone()

    @staticmethod
    def get_projects_by_user(user_email: str):
        if Projects_database.__Db_is_connected is None:
            return {"message": "db is not connected"}

        conn = Projects_database.__Db_is_connected
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT ProjectId, ProjectName, ProjectStatus
            FROM S_Projects
            WHERE UserEmail = ?
            ORDER BY UpdatedAt DESC
            """,
            (user_email,)
        )

        return cursor.fetchall()

    @staticmethod
    def rename_project(project_id: int, new_name: str):
        if Projects_database.__Db_is_connected is None:
            return {"message": "db is not connected"}

        conn = Projects_database.__Db_is_connected
        cursor = conn.cursor()

        cursor.execute(
            """
            UPDATE S_Projects
            SET ProjectName = ?,
                UpdatedAt = CURRENT_TIMESTAMP
            WHERE ProjectId = ?
            """,
            (new_name, project_id)
        )

        conn.commit()
        return cursor.rowcount > 0

    @staticmethod
    def get_project_name(project_id: int):
        if Projects_database.__Db_is_connected is None:
            return {"message": "db is not connected"}

        conn = Projects_database.__Db_is_connected
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT ProjectName
            FROM S_Projects
            WHERE ProjectId = ?
            LIMIT 1
            """,
            (project_id,)
        )

        row = cursor.fetchone()
        return row["ProjectName"] if row else None

    @staticmethod
    def delete_project(project_id: int):
        if Projects_database.__Db_is_connected is None:
            return {"message": "db is not connected"}

        conn = Projects_database.__Db_is_connected
        cursor = conn.cursor()

        cursor.execute(
            """
            DELETE FROM S_Projects
            WHERE ProjectId = ?
            """,
            (project_id,)
        )

        conn.commit()
        return cursor.rowcount > 0

    @staticmethod
    def user_is_project_owner(project_id: int, user_email: str):
        if Projects_database.__Db_is_connected is None:
            return {"message": "db is not connected"}

        conn = Projects_database.__Db_is_connected
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT 1
            FROM S_Projects
            WHERE ProjectId = ?
              AND UserEmail = ?
            LIMIT 1
            """,
            (project_id, user_email)
        )

        return cursor.fetchone() is not None

    @staticmethod
    def set_current_project(user_email: str, project_id: int):
        if Projects_database.__Db_is_connected is None:
            return {"message": "db is not connected"}

        conn = Projects_database.__Db_is_connected
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT 1
            FROM S_Projects
            WHERE ProjectId = ?
              AND UserEmail = ?
            LIMIT 1
            """,
            (project_id, user_email)
        )

        if cursor.fetchone() is None:
            return {"error": "Project does not exist or access denied"}

        return {"success": True, "current_project_id": project_id}

    @staticmethod
    def get_current_project(user_email: str, current_project_id: int | None = None):
        if Projects_database.__Db_is_connected is None:
            return {"message": "db is not connected"}

        if current_project_id is None:
            return {"error": "No current project supplied"}

        conn = Projects_database.__Db_is_connected
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT ProjectId
            FROM S_Projects
            WHERE ProjectId = ?
              AND UserEmail = ?
            LIMIT 1
            """,
            (current_project_id, user_email)
        )

        row = cursor.fetchone()
        return row["ProjectId"] if row else None
