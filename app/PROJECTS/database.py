from app.CORE.connection import master_connection


class PROJECT_COL:
    ProjectId = 0
    UserEmail = 1
    ProjectName = 2
    ProjectStatus = 3
    CreatedAt = 4
    UpdatedAt = 5


class Projects_database:

    # =========================
    # Reads
    # =========================

    @staticmethod
    def get_active_projects_by_email(user_email: str):
        with master_connection() as cursor:
            return cursor.execute(
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
                (user_email,),
            ).fetchall()

    @staticmethod
    def get_project_by_id(project_id: int):
        with master_connection() as cursor:
            return cursor.execute(
                """
                SELECT *
                FROM S_Projects
                WHERE ProjectId = ?
                LIMIT 1
                """,
                (project_id,),
            ).fetchone()

    @staticmethod
    def get_project_for_user(project_id: int, user_email: str):
        with master_connection() as cursor:
            return cursor.execute(
                """
                SELECT *
                FROM S_Projects
                WHERE ProjectId = ?
                  AND UserEmail = ?
                LIMIT 1
                """,
                (project_id, user_email),
            ).fetchone()

    @staticmethod
    def get_projects_by_user(user_email: str):
        with master_connection() as cursor:
            return cursor.execute(
                """
                SELECT ProjectId, ProjectName, ProjectStatus
                FROM S_Projects
                WHERE UserEmail = ?
                ORDER BY UpdatedAt DESC
                """,
                (user_email,),
            ).fetchall()

    @staticmethod
    def get_project_name(project_id: int):
        with master_connection() as cursor:
            row = cursor.execute(
                """
                SELECT ProjectName
                FROM S_Projects
                WHERE ProjectId = ?
                LIMIT 1
                """,
                (project_id,),
            ).fetchone()
            return row[0] if row else None

    # =========================
    # Writes
    # =========================

    @staticmethod
    def create_project(user_email: str, project_name: str):
        with master_connection() as cursor:
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
                (user_email, project_name),
            )
            return cursor.execute("SELECT last_insert_rowid()").fetchone()[0]

    @staticmethod
    def rename_project(project_id: int, new_name: str):
        with master_connection() as cursor:
            cursor.execute(
                """
                UPDATE S_Projects
                SET ProjectName = ?,
                    UpdatedAt = CURRENT_TIMESTAMP
                WHERE ProjectId = ?
                """,
                (new_name, project_id),
            )
            return cursor.rowcount() > 0

    @staticmethod
    def delete_project(project_id: int):
        with master_connection() as cursor:
            cursor.execute(
                """
                DELETE FROM S_Projects
                WHERE ProjectId = ?
                """,
                (project_id,),
            )
            return cursor.rowcount() > 0

    # =========================
    # Status / Ownership
    # =========================

    @staticmethod
    def set_project_status(user_email: str, project_id: str, status: str):
        with master_connection() as cursor:
            cursor.execute(
                """
                UPDATE S_Projects
                SET ProjectStatus = NULL
                WHERE UserEmail = ?
                """,
                (user_email,),
            )

            cursor.execute(
                """
                UPDATE S_Projects
                SET ProjectStatus = ?, UpdatedAt = datetime('now')
                WHERE UserEmail = ? AND ProjectId = ?
                """,
                (status, user_email, project_id),
            )

            return cursor.rowcount() > 0

    @staticmethod
    def project_name_exists(user_email: str, project_name: str):
        with master_connection() as cursor:
            return (
                cursor.execute(
                    """
                    SELECT 1
                    FROM S_Projects
                    WHERE UserEmail = ?
                      AND ProjectName = ?
                    LIMIT 1
                    """,
                    (user_email, project_name),
                ).fetchone()
                is not None
            )

    @staticmethod
    def user_is_project_owner(project_id: int, user_email: str):
        with master_connection() as cursor:
            return (
                cursor.execute(
                    """
                    SELECT 1
                    FROM S_Projects
                    WHERE ProjectId = ?
                      AND UserEmail = ?
                    LIMIT 1
                    """,
                    (project_id, user_email),
                ).fetchone()
                is not None
            )

    # =========================
    # Current Project (logic only)
    # =========================

    @staticmethod
    def set_current_project(user_email: str, project_id: int):
        with master_connection() as cursor:
            exists = cursor.execute(
                """
                SELECT 1
                FROM S_Projects
                WHERE ProjectId = ?
                  AND UserEmail = ?
                LIMIT 1
                """,
                (project_id, user_email),
            ).fetchone()

            if exists is None:
                return {"error": "Project does not exist or access denied"}

            return {"success": True, "current_project_id": project_id}

    @staticmethod
    def get_current_project(user_email: str, current_project_id: int | None = None):
        if current_project_id is None:
            return {"error": "No current project supplied"}

        with master_connection() as cursor:
            row = cursor.execute(
                """
                SELECT ProjectId
                FROM S_Projects
                WHERE ProjectId = ?
                  AND UserEmail = ?
                LIMIT 1
                """,
                (current_project_id, user_email),
            ).fetchone()

            return row[0] if row else None
