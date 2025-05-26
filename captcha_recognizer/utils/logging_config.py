#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
日志配置模块
提供结构化日志记录功能
"""

import logging
import logging.handlers
import json
import os
import sys
import uuid
from datetime import datetime
from typing import Dict, Any, Optional
import threading

# 线程本地存储，用于存储请求ID
_local = threading.local()


class JSONFormatter(logging.Formatter):
    """JSON格式化器"""
    
    def __init__(self, include_extra: bool = True):
        """
        初始化JSON格式化器
        
        Args:
            include_extra: 是否包含额外字段
        """
        super().__init__()
        self.include_extra = include_extra
    
    def format(self, record: logging.LogRecord) -> str:
        """
        格式化日志记录为JSON格式
        
        Args:
            record: 日志记录
            
        Returns:
            JSON格式的日志字符串
        """
        # 基础日志信息
        log_entry = {
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno,
            'thread': record.thread,
            'thread_name': record.threadName,
            'process': record.process
        }
        
        # 添加请求ID（如果存在）
        request_id = get_request_id()
        if request_id:
            log_entry['request_id'] = request_id
        
        # 添加异常信息
        if record.exc_info:
            log_entry['exception'] = self.formatException(record.exc_info)
        
        # 添加额外字段
        if self.include_extra:
            for key, value in record.__dict__.items():
                if key not in log_entry and not key.startswith('_'):
                    # 跳过标准字段
                    if key not in ['name', 'msg', 'args', 'levelname', 'levelno', 
                                  'pathname', 'filename', 'module', 'lineno', 
                                  'funcName', 'created', 'msecs', 'relativeCreated',
                                  'thread', 'threadName', 'processName', 'process',
                                  'getMessage', 'exc_info', 'exc_text', 'stack_info']:
                        log_entry[key] = value
        
        return json.dumps(log_entry, ensure_ascii=False, default=str)


class RequestIDFilter(logging.Filter):
    """请求ID过滤器"""
    
    def filter(self, record: logging.LogRecord) -> bool:
        """
        为日志记录添加请求ID
        
        Args:
            record: 日志记录
            
        Returns:
            总是返回True
        """
        record.request_id = get_request_id()
        return True


def generate_request_id() -> str:
    """
    生成新的请求ID
    
    Returns:
        UUID格式的请求ID
    """
    return str(uuid.uuid4())


def set_request_id(request_id: Optional[str] = None) -> str:
    """
    设置当前线程的请求ID
    
    Args:
        request_id: 请求ID，如果为None则生成新的
        
    Returns:
        设置的请求ID
    """
    if request_id is None:
        request_id = generate_request_id()
    
    _local.request_id = request_id
    return request_id


def get_request_id() -> Optional[str]:
    """
    获取当前线程的请求ID
    
    Returns:
        请求ID，如果不存在则返回None
    """
    return getattr(_local, 'request_id', None)


def clear_request_id():
    """清除当前线程的请求ID"""
    if hasattr(_local, 'request_id'):
        delattr(_local, 'request_id')


def setup_logging(
    level: str = 'INFO',
    log_file: Optional[str] = None,
    max_bytes: int = 10 * 1024 * 1024,  # 10MB
    backup_count: int = 5,
    json_format: bool = True,
    console_output: bool = True
) -> logging.Logger:
    """
    设置日志配置
    
    Args:
        level: 日志级别
        log_file: 日志文件路径
        max_bytes: 日志文件最大大小
        backup_count: 备份文件数量
        json_format: 是否使用JSON格式
        console_output: 是否输出到控制台
        
    Returns:
        配置好的根日志器
    """
    # 获取根日志器
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, level.upper()))
    
    # 清除现有处理器
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # 创建格式化器
    if json_format:
        formatter = JSONFormatter()
    else:
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
    
    # 控制台处理器
    if console_output:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(formatter)
        console_handler.addFilter(RequestIDFilter())
        root_logger.addHandler(console_handler)
    
    # 文件处理器
    if log_file:
        # 确保日志目录存在
        log_dir = os.path.dirname(log_file)
        if log_dir and not os.path.exists(log_dir):
            os.makedirs(log_dir)
        
        file_handler = logging.handlers.RotatingFileHandler(
            log_file,
            maxBytes=max_bytes,
            backupCount=backup_count,
            encoding='utf-8'
        )
        file_handler.setFormatter(formatter)
        file_handler.addFilter(RequestIDFilter())
        root_logger.addHandler(file_handler)
    
    return root_logger


def get_logger(name: str) -> logging.Logger:
    """
    获取指定名称的日志器
    
    Args:
        name: 日志器名称
        
    Returns:
        日志器实例
    """
    return logging.getLogger(name)


class LoggerMixin:
    """日志器混入类"""
    
    @property
    def logger(self) -> logging.Logger:
        """获取当前类的日志器"""
        return get_logger(self.__class__.__module__ + '.' + self.__class__.__name__)


def log_function_call(func):
    """
    函数调用日志装饰器
    
    Args:
        func: 要装饰的函数
        
    Returns:
        装饰后的函数
    """
    def wrapper(*args, **kwargs):
        logger = get_logger(func.__module__)
        
        # 记录函数调用开始
        logger.info(
            f"函数调用开始: {func.__name__}",
            extra={
                'function': func.__name__,
                'args_count': len(args),
                'kwargs_keys': list(kwargs.keys()),
                'event_type': 'function_call_start'
            }
        )
        
        try:
            result = func(*args, **kwargs)
            
            # 记录函数调用成功
            logger.info(
                f"函数调用成功: {func.__name__}",
                extra={
                    'function': func.__name__,
                    'event_type': 'function_call_success'
                }
            )
            
            return result
            
        except Exception as e:
            # 记录函数调用失败
            logger.error(
                f"函数调用失败: {func.__name__}",
                extra={
                    'function': func.__name__,
                    'error': str(e),
                    'error_type': type(e).__name__,
                    'event_type': 'function_call_error'
                },
                exc_info=True
            )
            raise
    
    return wrapper


# 默认日志配置
def configure_default_logging():
    """配置默认日志设置"""
    log_level = os.getenv('LOG_LEVEL', 'INFO')
    log_file = os.getenv('LOG_FILE', 'logs/captcha_recognizer.log')
    json_format = os.getenv('LOG_JSON_FORMAT', 'true').lower() == 'true'
    
    setup_logging(
        level=log_level,
        log_file=log_file,
        json_format=json_format
    )


# 在模块导入时配置默认日志
configure_default_logging()
