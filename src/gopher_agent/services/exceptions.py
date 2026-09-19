"""不依赖 HTTP 的业务异常。"""


class UsernameAlreadyExistsError(Exception):
    """规范化后的用户名已经存在。"""


class InvalidCredentialsError(Exception):
    """登录凭据无效。"""
