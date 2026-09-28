"""不依赖 HTTP 的业务异常。"""


class UsernameAlreadyExistsError(Exception):
    """规范化后的用户名已经存在。"""


class InvalidCredentialsError(Exception):
    """登录凭据无效。"""


class ProfileParserUnavailableError(Exception):
    """自然语言档案解析所需的模型资源不可用。"""


class ProfileParsingError(Exception):
    """模型调用失败或 structured output 不符合档案契约。"""


class ProfileSessionNotFoundError(Exception):
    """当前用户不存在指定的档案解析 session。"""


class ProfileSessionConflictError(Exception):
    """已完成的 session 被用于确认不同的档案内容。"""
