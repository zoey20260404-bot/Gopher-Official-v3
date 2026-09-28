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


class ProfileInterviewConflictError(Exception):
    """档案访谈 session 状态或问题版本已经发生变化。"""


class UserProfileNotConfirmedError(Exception):
    """当前用户尚未确认可用于岗位匹配的权威档案。"""


class PositionCandidateLimitExceededError(Exception):
    """岗位粗筛候选数超过确定性匹配的安全上限。"""

    def __init__(self, candidate_count: int, limit: int) -> None:
        self.candidate_count = candidate_count
        self.limit = limit
        super().__init__(f"候选岗位数 {candidate_count} 超过上限 {limit}")


class ReportNotFoundError(Exception):
    """当前用户不存在指定报告。"""


class ReportConflictError(Exception):
    """报告状态、审批请求或 graph 结果存在冲突。"""


class ReportNoCandidatesError(Exception):
    """当前过滤条件下没有可进入报告的候选岗位。"""


class ReportGenerationError(Exception):
    """报告 graph 或模型生成失败。"""


class ReportWorkflowUnavailableError(Exception):
    """报告 workflow 所需的模型或 checkpoint 资源不可用。"""
