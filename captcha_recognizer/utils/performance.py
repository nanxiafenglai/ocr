#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
性能监控模块
提供性能监控装饰器和指标收集功能
"""

import time
import threading
from functools import wraps
from typing import Dict, Any, Optional, Callable, List
from collections import defaultdict, deque
import statistics
import logging

logger = logging.getLogger(__name__)


class PerformanceMetrics:
    """性能指标收集器"""
    
    def __init__(self, max_history: int = 1000):
        """
        初始化性能指标收集器
        
        Args:
            max_history: 最大历史记录数量
        """
        self.max_history = max_history
        self.metrics: Dict[str, Dict[str, Any]] = defaultdict(lambda: {
            'call_count': 0,
            'total_time': 0.0,
            'min_time': float('inf'),
            'max_time': 0.0,
            'success_count': 0,
            'error_count': 0,
            'history': deque(maxlen=max_history)
        })
        self.lock = threading.RLock()
    
    def record_call(self, 
                   function_name: str, 
                   duration: float, 
                   success: bool = True,
                   error: Optional[str] = None):
        """
        记录函数调用性能数据
        
        Args:
            function_name: 函数名称
            duration: 执行时间（秒）
            success: 是否成功
            error: 错误信息
        """
        with self.lock:
            metric = self.metrics[function_name]
            
            # 更新基础统计
            metric['call_count'] += 1
            metric['total_time'] += duration
            metric['min_time'] = min(metric['min_time'], duration)
            metric['max_time'] = max(metric['max_time'], duration)
            
            if success:
                metric['success_count'] += 1
            else:
                metric['error_count'] += 1
            
            # 记录历史数据
            metric['history'].append({
                'timestamp': time.time(),
                'duration': duration,
                'success': success,
                'error': error
            })
    
    def get_stats(self, function_name: str) -> Dict[str, Any]:
        """
        获取函数性能统计信息
        
        Args:
            function_name: 函数名称
            
        Returns:
            性能统计信息
        """
        with self.lock:
            if function_name not in self.metrics:
                return {}
            
            metric = self.metrics[function_name]
            
            if metric['call_count'] == 0:
                return metric.copy()
            
            # 计算平均时间
            avg_time = metric['total_time'] / metric['call_count']
            
            # 计算成功率
            success_rate = metric['success_count'] / metric['call_count']
            
            # 计算最近的性能数据
            recent_durations = [
                record['duration'] for record in list(metric['history'])[-100:]
                if record['success']
            ]
            
            recent_stats = {}
            if recent_durations:
                recent_stats = {
                    'recent_avg': statistics.mean(recent_durations),
                    'recent_median': statistics.median(recent_durations),
                    'recent_p95': statistics.quantiles(recent_durations, n=20)[18] if len(recent_durations) >= 20 else max(recent_durations),
                    'recent_p99': statistics.quantiles(recent_durations, n=100)[98] if len(recent_durations) >= 100 else max(recent_durations)
                }
            
            return {
                'call_count': metric['call_count'],
                'success_count': metric['success_count'],
                'error_count': metric['error_count'],
                'success_rate': success_rate,
                'total_time': metric['total_time'],
                'avg_time': avg_time,
                'min_time': metric['min_time'] if metric['min_time'] != float('inf') else 0,
                'max_time': metric['max_time'],
                **recent_stats
            }
    
    def get_all_stats(self) -> Dict[str, Dict[str, Any]]:
        """
        获取所有函数的性能统计信息
        
        Returns:
            所有函数的性能统计信息
        """
        with self.lock:
            return {
                func_name: self.get_stats(func_name)
                for func_name in self.metrics.keys()
            }
    
    def reset_stats(self, function_name: Optional[str] = None):
        """
        重置性能统计信息
        
        Args:
            function_name: 函数名称，如果为None则重置所有
        """
        with self.lock:
            if function_name:
                if function_name in self.metrics:
                    del self.metrics[function_name]
            else:
                self.metrics.clear()


# 全局性能指标收集器
performance_metrics = PerformanceMetrics()


def monitor_performance(
    include_args: bool = False,
    include_result: bool = False,
    log_slow_calls: bool = True,
    slow_threshold: float = 1.0
):
    """
    性能监控装饰器
    
    Args:
        include_args: 是否在日志中包含参数信息
        include_result: 是否在日志中包含返回结果
        log_slow_calls: 是否记录慢调用
        slow_threshold: 慢调用阈值（秒）
        
    Returns:
        装饰器函数
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            function_name = f"{func.__module__}.{func.__qualname__}"
            start_time = time.time()
            
            # 准备日志额外信息
            extra_info = {
                'function': func.__name__,
                'module': func.__module__,
                'event_type': 'performance_monitor'
            }
            
            if include_args:
                extra_info['args_count'] = len(args)
                extra_info['kwargs_keys'] = list(kwargs.keys())
            
            try:
                # 执行函数
                result = func(*args, **kwargs)
                success = True
                error = None
                
                if include_result:
                    extra_info['result_type'] = type(result).__name__
                    if hasattr(result, '__len__'):
                        extra_info['result_length'] = len(result)
                
            except Exception as e:
                result = None
                success = False
                error = str(e)
                extra_info['error'] = error
                extra_info['error_type'] = type(e).__name__
                raise
            
            finally:
                # 计算执行时间
                end_time = time.time()
                duration = end_time - start_time
                
                # 记录性能指标
                performance_metrics.record_call(
                    function_name, 
                    duration, 
                    success, 
                    error
                )
                
                # 更新日志信息
                extra_info.update({
                    'duration': duration,
                    'success': success,
                    'duration_ms': duration * 1000
                })
                
                # 记录日志
                if success:
                    if log_slow_calls and duration > slow_threshold:
                        logger.warning(
                            f"慢调用检测: {func.__name__} 执行时间 {duration:.3f}s",
                            extra=extra_info
                        )
                    else:
                        logger.debug(
                            f"函数执行完成: {func.__name__}",
                            extra=extra_info
                        )
                else:
                    logger.error(
                        f"函数执行失败: {func.__name__}",
                        extra=extra_info
                    )
            
            return result
        
        return wrapper
    return decorator


def get_performance_summary() -> Dict[str, Any]:
    """
    获取性能摘要信息
    
    Returns:
        性能摘要信息
    """
    all_stats = performance_metrics.get_all_stats()
    
    if not all_stats:
        return {
            'total_functions': 0,
            'total_calls': 0,
            'total_errors': 0,
            'overall_success_rate': 0.0
        }
    
    total_calls = sum(stats['call_count'] for stats in all_stats.values())
    total_errors = sum(stats['error_count'] for stats in all_stats.values())
    total_success = sum(stats['success_count'] for stats in all_stats.values())
    
    overall_success_rate = total_success / total_calls if total_calls > 0 else 0.0
    
    # 找出最慢的函数
    slowest_functions = sorted(
        [(name, stats) for name, stats in all_stats.items() if stats['call_count'] > 0],
        key=lambda x: x[1]['avg_time'],
        reverse=True
    )[:5]
    
    # 找出错误最多的函数
    error_prone_functions = sorted(
        [(name, stats) for name, stats in all_stats.items() if stats['error_count'] > 0],
        key=lambda x: x[1]['error_count'],
        reverse=True
    )[:5]
    
    return {
        'total_functions': len(all_stats),
        'total_calls': total_calls,
        'total_errors': total_errors,
        'total_success': total_success,
        'overall_success_rate': overall_success_rate,
        'slowest_functions': [
            {
                'name': name,
                'avg_time': stats['avg_time'],
                'call_count': stats['call_count']
            }
            for name, stats in slowest_functions
        ],
        'error_prone_functions': [
            {
                'name': name,
                'error_count': stats['error_count'],
                'error_rate': stats['error_count'] / stats['call_count']
            }
            for name, stats in error_prone_functions
        ]
    }


def log_performance_summary():
    """记录性能摘要到日志"""
    summary = get_performance_summary()
    
    logger.info(
        "性能监控摘要",
        extra={
            'event_type': 'performance_summary',
            **summary
        }
    )


class PerformanceContext:
    """性能监控上下文管理器"""
    
    def __init__(self, name: str, log_result: bool = True):
        """
        初始化性能监控上下文
        
        Args:
            name: 监控名称
            log_result: 是否记录结果到日志
        """
        self.name = name
        self.log_result = log_result
        self.start_time = None
        self.end_time = None
    
    def __enter__(self):
        self.start_time = time.time()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.end_time = time.time()
        duration = self.end_time - self.start_time
        
        success = exc_type is None
        error = str(exc_val) if exc_val else None
        
        # 记录性能指标
        performance_metrics.record_call(
            self.name,
            duration,
            success,
            error
        )
        
        # 记录日志
        if self.log_result:
            extra_info = {
                'context_name': self.name,
                'duration': duration,
                'duration_ms': duration * 1000,
                'success': success,
                'event_type': 'performance_context'
            }
            
            if error:
                extra_info['error'] = error
            
            if success:
                logger.debug(f"性能监控: {self.name}", extra=extra_info)
            else:
                logger.error(f"性能监控失败: {self.name}", extra=extra_info)
    
    @property
    def duration(self) -> Optional[float]:
        """获取执行时间"""
        if self.start_time and self.end_time:
            return self.end_time - self.start_time
        return None
