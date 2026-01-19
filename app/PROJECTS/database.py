from app.CORE.connection import master_connection
from app.CORE.DB import with_master_cursor

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

    #used in MODELS router 
    @staticmethod
    def get_curent_active_project_id_by_email(cursor, user_email: str):
           row = cursor.execute(
                """
                SELECT
                    ProjectId
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
           
           return row[0] if row else None

    @staticmethod
    def get_active_projects_by_email(cursor,user_email: str):
        #with master_connection() as cursor:
            return cursor.execute(
                """
                SELECT
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

    #used in MODELS router
    @staticmethod
    def get_project_id_for_user(cursor, user_email: str, project_name: str):
        row = cursor.execute(
            """
            SELECT ProjectID
            FROM S_Projects
            WHERE UserEmail = ?
              AND ProjectName = ?
            LIMIT 1
            """,
            (user_email, project_name),
        ).fetchone()

        return row[PROJECT_COL.ProjectId] if row else None

    @staticmethod
    def get_project_for_user(cursor, user_email: str, project_name: str):
        #with master_connection() as cursor:
            return cursor.execute(
                """
                SELECT *
                FROM S_Projects
                WHERE UserEmail = ?
                  AND ProjectName = ?
                LIMIT 1
                """,
                (user_email, project_name),
            ).fetchone()

    @staticmethod
    def get_projects_by_user(cursor ,user_email: str):
        #with master_connection() as cursor:
            return cursor.execute(
                """
                SELECT ProjectName, ProjectStatus
                FROM S_Projects
                WHERE UserEmail = ?
                ORDER BY UpdatedAt DESC
                """,
                (user_email,),
            ).fetchall()

    @staticmethod
    def get_project_name(cursor ,user_email: str, project_name: str):
        #with master_connection() as cursor:
            row = cursor.execute(
                """
                SELECT ProjectName
                FROM S_Projects
                WHERE UserEmail = ?
                  AND ProjectName = ?
                LIMIT 1
                """,
                (user_email, project_name),
            ).fetchone()
            return row[0] if row else None

    # =========================
    # Writes
    # =========================

    @staticmethod
    def create_project(cursor ,user_email: str, project_name: str):
        #with master_connection() as cursor:
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
            return project_name  

    @staticmethod
    def rename_project(cursor ,user_email: str, old_name: str, new_name: str):
        #with master_connection() as cursor:
            cursor.execute(
                """
                UPDATE S_Projects
                SET ProjectName = ?,
                    UpdatedAt = CURRENT_TIMESTAMP
                WHERE UserEmail = ?
                  AND ProjectName = ?
                """,
                (new_name, user_email, old_name),
            )

            row = cursor.execute(
                """
                SELECT 1
                FROM S_Projects
                WHERE UserEmail = ? AND ProjectName = ?
                LIMIT 1
                """,
                (user_email, new_name),
            ).fetchone()

            return row is not None
            

    @staticmethod
    def delete_project(cursor ,user_email: str, project_name: str):
        #with master_connection() as cursor:
            cursor.execute(
                """
                DELETE FROM S_Projects
                WHERE UserEmail = ?
                  AND ProjectName = ?
                """,
                (user_email, project_name),
            )

            row = cursor.execute(
                """
                SELECT 1
                FROM S_Projects
                WHERE UserEmail = ? AND ProjectName = ?
                LIMIT 1
                """,
                (user_email, project_name),
            ).fetchone()

            return row is None
            

    # =========================
    # Status / Ownership
    # =========================

    @staticmethod
    def set_project_status(cursor ,user_email: str, project_name: str, status: str):
        #with master_connection() as cursor:
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
                WHERE UserEmail = ?
                  AND ProjectName = ?
                """,
                (status, user_email, project_name),
            )

            row = cursor.execute(
                """
                SELECT 1
                FROM S_Projects
                WHERE UserEmail = ? AND ProjectName = ? AND ProjectStatus = ?
                LIMIT 1
                """,
                (user_email, project_name, status),
            ).fetchone()

            return row is not None

            #return cursor.rowcount > 0

    @staticmethod
    def project_name_exists(cursor , user_email: str, project_name: str):
        #with master_connection() as cursor:
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
    def user_is_project_owner(cursor ,user_email: str, project_name: str):
        #with master_connection() as cursor:
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

    # =========================
    # Current Project 
    # =========================

    @staticmethod
    def set_current_project(cursor , user_email: str, project_name: str):
        #with master_connection() as cursor:
            exists = cursor.execute(
                """
                SELECT 1
                FROM S_Projects
                WHERE UserEmail = ?
                  AND ProjectName = ?
                LIMIT 1
                """,
                (user_email, project_name),
            ).fetchone()

            if exists is None:
                return {"error": "Project does not exist or access denied"}

            return {"success": True, "current_project": project_name}

    @staticmethod
    def get_current_project(cursor, user_email: str, current_project_name: str | None = None):
        if current_project_name is None:
            return {"error": "No current project supplied"}

        #with master_connection() as cursor:
        row = cursor.execute(
            """
            SELECT ProjectName
            FROM S_Projects
            WHERE UserEmail = ?
              AND ProjectName = ?
            LIMIT 1
            """,
            (user_email, current_project_name),
        ).fetchone()   
        return row[0] if row else None
