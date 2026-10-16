"""统一响应模型与异常处理"""
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel


class ApiResponse(BaseModel):
    code: int = 0
    message: str = "ok"
    data: object = None
    total: int = 0


def ok(data=None, total: int = 0, message: str = "ok"):
    return {"code": 0, "message": message, "data": data, "total": total}


class BizError(Exception):
    """业务异常：携带 HTTP 状态码与错误信息"""

    def __init__(self, message: str, code: int = 400):
        self.message = message
        self.code = code
        super().__init__(message)


def register_exception_handlers(app: FastAPI):
    @app.exception_handler(BizError)
    async def biz_error_handler(request: Request, exc: BizError):
        return JSONResponse(
            status_code=exc.code,
            content={"code": exc.code, "message": exc.message, "data": None, "total": 0},
        )

    @app.exception_handler(Exception)
    async def unhandled_handler(request: Request, exc: Exception):
        return JSONResponse(
            status_code=500,
            content={"code": 500, "message": f"服务器错误: {exc}", "data": None, "total": 0},
        )
