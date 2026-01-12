from app.CORE.connection import master_connection


class USER_ROLE_COL:
    RoleId = 0
    RoleName = 1
    RoleDescription = 2
    CreatedAt = 3
    UpdatedAt = 4


class Admin_database:

    @staticmethod
    def get_role_by_id(role_id):
        with master_connection() as cursor:
            cursor.execute(
                """
                SELECT *
                FROM S_UserRoles
                WHERE RoleId = ?
                """,
                (role_id,)
            )

            role = cursor.fetchone()
            print("user role = ", role)
            return role
