from passlib.context import CryptContext

class PasswordHandler:
    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

    @staticmethod
    def get_hashed_password(password: str) -> str:
        return PasswordHandler.pwd_context.hash(password)

    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        return PasswordHandler.pwd_context.verify(plain_password, hashed_password)
