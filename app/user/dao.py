from app.core.base_dao import BaseDAO
from app.user.models import User

class UserDAO(BaseDAO):
    model = User