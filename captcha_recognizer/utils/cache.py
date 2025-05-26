#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
缓存管理模块
提供图像哈希缓存和结果缓存功能
"""

import hashlib
import time
from functools import lru_cache
from typing import Optional, Dict, Any, Tuple
import threading


class ImageHashCache:
    """
    图像哈希缓存类
    用于缓存图像识别结果，避免重复处理相同图像
    """
    
    def __init__(self, max_size: int = 1000, ttl: int = 3600):
        """
        初始化图像哈希缓存
        
        Args:
            max_size: 最大缓存条目数
            ttl: 缓存生存时间（秒）
        """
        self.max_size = max_size
        self.ttl = ttl
        self.cache: Dict[str, Dict[str, Any]] = {}
        self.access_times: Dict[str, float] = {}
        self.lock = threading.RLock()
    
    def get_image_hash(self, image_data: bytes) -> str:
        """
        计算图像数据的哈希值
        
        Args:
            image_data: 图像字节数据
            
        Returns:
            图像的MD5哈希值
        """
        return hashlib.md5(image_data).hexdigest()
    
    def get(self, image_hash: str) -> Optional[Dict[str, Any]]:
        """
        从缓存中获取识别结果
        
        Args:
            image_hash: 图像哈希值
            
        Returns:
            缓存的识别结果，如果不存在或已过期则返回None
        """
        with self.lock:
            if image_hash not in self.cache:
                return None
            
            # 检查是否过期
            cache_entry = self.cache[image_hash]
            if time.time() - cache_entry['timestamp'] > self.ttl:
                self._remove(image_hash)
                return None
            
            # 更新访问时间
            self.access_times[image_hash] = time.time()
            return cache_entry['result']
    
    def set(self, image_hash: str, result: Dict[str, Any]) -> None:
        """
        将识别结果存入缓存
        
        Args:
            image_hash: 图像哈希值
            result: 识别结果
        """
        with self.lock:
            # 如果缓存已满，移除最久未访问的条目
            if len(self.cache) >= self.max_size:
                self._evict_lru()
            
            current_time = time.time()
            self.cache[image_hash] = {
                'result': result,
                'timestamp': current_time
            }
            self.access_times[image_hash] = current_time
    
    def _remove(self, image_hash: str) -> None:
        """
        从缓存中移除指定条目
        
        Args:
            image_hash: 要移除的图像哈希值
        """
        if image_hash in self.cache:
            del self.cache[image_hash]
        if image_hash in self.access_times:
            del self.access_times[image_hash]
    
    def _evict_lru(self) -> None:
        """
        移除最久未访问的缓存条目
        """
        if not self.access_times:
            return
        
        # 找到最久未访问的条目
        lru_hash = min(self.access_times.keys(), 
                      key=lambda k: self.access_times[k])
        self._remove(lru_hash)
    
    def clear(self) -> None:
        """
        清空所有缓存
        """
        with self.lock:
            self.cache.clear()
            self.access_times.clear()
    
    def get_stats(self) -> Dict[str, Any]:
        """
        获取缓存统计信息
        
        Returns:
            缓存统计信息
        """
        with self.lock:
            current_time = time.time()
            expired_count = sum(
                1 for entry in self.cache.values()
                if current_time - entry['timestamp'] > self.ttl
            )
            
            return {
                'total_entries': len(self.cache),
                'expired_entries': expired_count,
                'active_entries': len(self.cache) - expired_count,
                'max_size': self.max_size,
                'ttl': self.ttl
            }


class LRUCache:
    """
    简单的LRU缓存实现
    用于缓存函数调用结果
    """
    
    def __init__(self, max_size: int = 128):
        """
        初始化LRU缓存
        
        Args:
            max_size: 最大缓存大小
        """
        self.max_size = max_size
        self.cache: Dict[str, Any] = {}
        self.access_order: list = []
        self.lock = threading.RLock()
    
    def get(self, key: str) -> Optional[Any]:
        """
        获取缓存值
        
        Args:
            key: 缓存键
            
        Returns:
            缓存值，如果不存在则返回None
        """
        with self.lock:
            if key in self.cache:
                # 移动到最近访问位置
                self.access_order.remove(key)
                self.access_order.append(key)
                return self.cache[key]
            return None
    
    def set(self, key: str, value: Any) -> None:
        """
        设置缓存值
        
        Args:
            key: 缓存键
            value: 缓存值
        """
        with self.lock:
            if key in self.cache:
                # 更新现有值
                self.cache[key] = value
                self.access_order.remove(key)
                self.access_order.append(key)
            else:
                # 添加新值
                if len(self.cache) >= self.max_size:
                    # 移除最久未使用的项
                    lru_key = self.access_order.pop(0)
                    del self.cache[lru_key]
                
                self.cache[key] = value
                self.access_order.append(key)
    
    def clear(self) -> None:
        """
        清空缓存
        """
        with self.lock:
            self.cache.clear()
            self.access_order.clear()


# 全局缓存实例
image_cache = ImageHashCache()
result_cache = LRUCache(max_size=256)


def cached_recognition(func):
    """
    识别结果缓存装饰器
    
    Args:
        func: 要缓存的识别函数
        
    Returns:
        装饰后的函数
    """
    def wrapper(image_data: bytes, captcha_type: str, **kwargs) -> Tuple[str, bool]:
        # 计算缓存键
        image_hash = image_cache.get_image_hash(image_data)
        cache_key = f"{image_hash}:{captcha_type}:{hash(str(sorted(kwargs.items())))}"
        
        # 尝试从缓存获取结果
        cached_result = image_cache.get(image_hash)
        if cached_result and cached_result.get('captcha_type') == captcha_type:
            # 检查参数是否匹配
            if cached_result.get('kwargs_hash') == hash(str(sorted(kwargs.items()))):
                return cached_result['result'], True  # 返回结果和缓存命中标志
        
        # 缓存未命中，执行实际识别
        result = func(image_data, captcha_type, **kwargs)
        
        # 将结果存入缓存
        cache_entry = {
            'result': result,
            'captcha_type': captcha_type,
            'kwargs_hash': hash(str(sorted(kwargs.items())))
        }
        image_cache.set(image_hash, cache_entry)
        
        return result, False  # 返回结果和缓存未命中标志
    
    return wrapper
