#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
统一错误处理模块
定义错误码体系和异常类
"""

from typing import Any, Optional, Dict
import traceback
import logging

logger = logging.getLogger(__name__)


class ErrorCode:
    """错误码定义"""
    
    # 通用错误 (1000-1999)
    SUCCESS = 0
    UNKNOWN_ERROR = 1000
    INVALID_PARAMETER = 1001
    MISSING_PARAMETER = 1002
    INVALID_REQUEST_FORMAT = 1003
    INTERNAL_ERROR = 1004
    
    # 认证错误 (2000-2999)
    UNAUTHORIZED = 2000
    INVALID_API_KEY = 2001
    RATE_LIMIT_EXCEEDED = 2002
    PERMISSION_DENIED = 2003
    TOKEN_EXPIRED = 2004
    
    # 业务错误 (3000-3999)
    UNSUPPORTED_CAPTCHA_TYPE = 3000
    INVALID_IMAGE_FORMAT = 3001
    IMAGE_TOO_LARGE = 3002
    IMAGE_TOO_SMALL = 3003
    RECOGNITION_FAILED = 3004
    PROCESSING_TIMEOUT = 3005
    INVALID_IMAGE_DATA = 3006
    
    # 系统错误 (4000-4999)
    DATABASE_ERROR = 4000
    CACHE_ERROR = 4001
    NETWORK_ERROR = 4002
    FILE_SYSTEM_ERROR = 4003
    EXTERNAL_SERVICE_ERROR = 4004


class CaptchaRecognizerException(Exception):
    """验证码识别器基础异常类"""
    
    def __init__(self, 
                 error_code: int, 
                 message: str, 
                 details: Optional[Any] = None,
                 cause: Optional[Exception] = None):
        """
        初始化异常
        
        Args:
            error_code: 错误码
            message: 错误消息
            details: 详细错误信息
            cause: 原始异常
        """
        self.error_code = error_code
        self.message = message
        self.details = details
        self.cause = cause
        super().__init__(message)
    
    def to_dict(self) -> Dict[str, Any]:
        """
        将异常转换为字典格式
        
        Returns:
            异常信息字典
        """
        result = {
            'success': False,
            'error_code': self.error_code,
            'message': self.message
        }
        
        if self.details is not None:
            result['details'] = self.details
        
        if self.cause is not None:
            result['cause'] = str(self.cause)
        
        return result


class ValidationError(CaptchaRecognizerException):
    """参数验证错误"""
    
    def __init__(self, message: str, details: Optional[Any] = None):
        super().__init__(ErrorCode.INVALID_PARAMETER, message, details)


class AuthenticationError(CaptchaRecognizerException):
    """认证错误"""
    
    def __init__(self, message: str = "认证失败", details: Optional[Any] = None):
        super().__init__(ErrorCode.UNAUTHORIZED, message, details)


class RateLimitError(CaptchaRecognizerException):
    """速率限制错误"""
    
    def __init__(self, message: str = "请求频率超出限制", details: Optional[Any] = None):
        super().__init__(ErrorCode.RATE_LIMIT_EXCEEDED, message, details)


class UnsupportedCaptchaTypeError(CaptchaRecognizerException):
    """不支持的验证码类型错误"""
    
    def __init__(self, captcha_type: str, supported_types: list):
        message = f"不支持的验证码类型: {captcha_type}"
        details = {
            'provided_type': captcha_type,
            'supported_types': supported_types
        }
        super().__init__(ErrorCode.UNSUPPORTED_CAPTCHA_TYPE, message, details)


class InvalidImageError(CaptchaRecognizerException):
    """无效图像错误"""
    
    def __init__(self, message: str = "无效的图像数据", details: Optional[Any] = None):
        super().__init__(ErrorCode.INVALID_IMAGE_FORMAT, message, details)


class ImageTooLargeError(CaptchaRecognizerException):
    """图像过大错误"""
    
    def __init__(self, size: int, max_size: int):
        message = f"图像大小超出限制: {size} bytes (最大: {max_size} bytes)"
        details = {
            'actual_size': size,
            'max_size': max_size
        }
        super().__init__(ErrorCode.IMAGE_TOO_LARGE, message, details)


class RecognitionFailedError(CaptchaRecognizerException):
    """识别失败错误"""
    
    def __init__(self, message: str = "验证码识别失败", details: Optional[Any] = None):
        super().__init__(ErrorCode.RECOGNITION_FAILED, message, details)


class ProcessingTimeoutError(CaptchaRecognizerException):
    """处理超时错误"""
    
    def __init__(self, timeout: float):
        message = f"处理超时: {timeout}秒"
        details = {'timeout': timeout}
        super().__init__(ErrorCode.PROCESSING_TIMEOUT, message, details)


def handle_exception(func):
    """
    异常处理装饰器
    
    Args:
        func: 要装饰的函数
        
    Returns:
        装饰后的函数
    """
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except CaptchaRecognizerException:
            # 重新抛出已知异常
            raise
        except FileNotFoundError as e:
            logger.error(f"文件未找到: {str(e)}")
            raise CaptchaRecognizerException(
                ErrorCode.FILE_SYSTEM_ERROR,
                "文件未找到",
                details={'file_path': str(e)},
                cause=e
            )
        except PermissionError as e:
            logger.error(f"权限错误: {str(e)}")
            raise CaptchaRecognizerException(
                ErrorCode.PERMISSION_DENIED,
                "权限不足",
                details={'error': str(e)},
                cause=e
            )
        except ValueError as e:
            logger.error(f"参数错误: {str(e)}")
            raise ValidationError(
                "参数验证失败",
                details={'error': str(e)}
            )
        except Exception as e:
            logger.error(f"未知错误: {str(e)}", exc_info=True)
            raise CaptchaRecognizerException(
                ErrorCode.UNKNOWN_ERROR,
                "系统内部错误",
                details={
                    'error': str(e),
                    'traceback': traceback.format_exc()
                },
                cause=e
            )
    
    return wrapper


def create_error_response(error_code: int, 
                         message: str, 
                         details: Optional[Any] = None) -> Dict[str, Any]:
    """
    创建标准错误响应
    
    Args:
        error_code: 错误码
        message: 错误消息
        details: 详细信息
        
    Returns:
        标准错误响应字典
    """
    response = {
        'success': False,
        'error_code': error_code,
        'message': message
    }
    
    if details is not None:
        response['details'] = details
    
    return response


def create_success_response(data: Any, 
                           message: str = "操作成功") -> Dict[str, Any]:
    """
    创建标准成功响应
    
    Args:
        data: 响应数据
        message: 成功消息
        
    Returns:
        标准成功响应字典
    """
    return {
        'success': True,
        'message': message,
        'data': data
    }
