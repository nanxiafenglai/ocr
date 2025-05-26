#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
配置管理模块
提供统一的配置管理功能
"""

import os
import json
import yaml
from typing import Dict, Any, Optional, Union
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


class ConfigManager:
    """配置管理器"""
    
    def __init__(self, config_file: Optional[str] = None):
        """
        初始化配置管理器
        
        Args:
            config_file: 配置文件路径
        """
        self._config: Dict[str, Any] = {}
        self._config_file = config_file
        self._load_default_config()
        
        if config_file:
            self.load_config(config_file)
        
        # 从环境变量加载配置
        self._load_env_config()
    
    def _load_default_config(self):
        """加载默认配置"""
        self._config = {
            # 应用配置
            'app': {
                'name': 'captcha-recognizer',
                'version': '1.0.0',
                'debug': False,
                'log_level': 'INFO'
            },
            
            # 识别配置
            'recognition': {
                'default_type': 'text',
                'max_image_size': 16 * 1024 * 1024,  # 16MB
                'supported_formats': ['png', 'jpg', 'jpeg', 'gif', 'bmp'],
                'timeout': 30.0,
                'retry_count': 3
            },
            
            # 缓存配置
            'cache': {
                'enabled': True,
                'type': 'memory',  # memory, redis
                'max_size': 1000,
                'ttl': 3600,  # 1小时
                'redis_url': 'redis://localhost:6379/0'
            },
            
            # 日志配置
            'logging': {
                'level': 'INFO',
                'format': 'json',  # json, text
                'file': 'logs/captcha_recognizer.log',
                'max_bytes': 10 * 1024 * 1024,  # 10MB
                'backup_count': 5,
                'console_output': True
            },
            
            # 性能配置
            'performance': {
                'monitor_enabled': True,
                'slow_threshold': 2.0,
                'max_history': 1000
            },
            
            # API配置
            'api': {
                'host': '0.0.0.0',
                'port': 5000,
                'debug': False,
                'rate_limit': {
                    'enabled': True,
                    'default_limit': '1000 per hour',
                    'per_method_limits': {
                        'POST /api/recognize/upload': '100 per minute',
                        'POST /api/recognize/url': '50 per minute',
                        'POST /api/recognize/base64': '100 per minute'
                    }
                }
            },
            
            # 安全配置
            'security': {
                'api_key_required': False,
                'jwt_secret': 'your-secret-key',
                'jwt_expiration': 3600,  # 1小时
                'cors_enabled': True,
                'cors_origins': ['*']
            }
        }
    
    def _load_env_config(self):
        """从环境变量加载配置"""
        env_mappings = {
            'APP_NAME': 'app.name',
            'APP_DEBUG': 'app.debug',
            'LOG_LEVEL': 'logging.level',
            'LOG_FILE': 'logging.file',
            'CACHE_ENABLED': 'cache.enabled',
            'CACHE_TYPE': 'cache.type',
            'CACHE_TTL': 'cache.ttl',
            'REDIS_URL': 'cache.redis_url',
            'API_HOST': 'api.host',
            'API_PORT': 'api.port',
            'API_DEBUG': 'api.debug',
            'RATE_LIMIT_ENABLED': 'api.rate_limit.enabled',
            'API_KEY_REQUIRED': 'security.api_key_required',
            'JWT_SECRET': 'security.jwt_secret',
            'CORS_ENABLED': 'security.cors_enabled'
        }
        
        for env_key, config_path in env_mappings.items():
            env_value = os.getenv(env_key)
            if env_value is not None:
                self._set_nested_value(config_path, self._convert_env_value(env_value))
    
    def _convert_env_value(self, value: str) -> Union[str, int, float, bool]:
        """
        转换环境变量值为适当的类型
        
        Args:
            value: 环境变量值
            
        Returns:
            转换后的值
        """
        # 布尔值
        if value.lower() in ('true', 'false'):
            return value.lower() == 'true'
        
        # 整数
        try:
            return int(value)
        except ValueError:
            pass
        
        # 浮点数
        try:
            return float(value)
        except ValueError:
            pass
        
        # 字符串
        return value
    
    def _set_nested_value(self, path: str, value: Any):
        """
        设置嵌套配置值
        
        Args:
            path: 配置路径，如 'app.debug'
            value: 配置值
        """
        keys = path.split('.')
        current = self._config
        
        for key in keys[:-1]:
            if key not in current:
                current[key] = {}
            current = current[key]
        
        current[keys[-1]] = value
    
    def load_config(self, config_file: str):
        """
        从文件加载配置
        
        Args:
            config_file: 配置文件路径
        """
        config_path = Path(config_file)
        
        if not config_path.exists():
            logger.warning(f"配置文件不存在: {config_file}")
            return
        
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                if config_path.suffix.lower() in ['.yml', '.yaml']:
                    file_config = yaml.safe_load(f)
                elif config_path.suffix.lower() == '.json':
                    file_config = json.load(f)
                else:
                    logger.error(f"不支持的配置文件格式: {config_path.suffix}")
                    return
            
            # 合并配置
            self._merge_config(self._config, file_config)
            logger.info(f"成功加载配置文件: {config_file}")
            
        except Exception as e:
            logger.error(f"加载配置文件失败: {config_file}, 错误: {str(e)}")
    
    def _merge_config(self, base: Dict[str, Any], override: Dict[str, Any]):
        """
        合并配置字典
        
        Args:
            base: 基础配置
            override: 覆盖配置
        """
        for key, value in override.items():
            if key in base and isinstance(base[key], dict) and isinstance(value, dict):
                self._merge_config(base[key], value)
            else:
                base[key] = value
    
    def get(self, path: str, default: Any = None) -> Any:
        """
        获取配置值
        
        Args:
            path: 配置路径，如 'app.debug'
            default: 默认值
            
        Returns:
            配置值
        """
        keys = path.split('.')
        current = self._config
        
        try:
            for key in keys:
                current = current[key]
            return current
        except (KeyError, TypeError):
            return default
    
    def set(self, path: str, value: Any):
        """
        设置配置值
        
        Args:
            path: 配置路径
            value: 配置值
        """
        self._set_nested_value(path, value)
    
    def get_section(self, section: str) -> Dict[str, Any]:
        """
        获取配置段
        
        Args:
            section: 配置段名称
            
        Returns:
            配置段字典
        """
        return self.get(section, {})
    
    def save_config(self, config_file: Optional[str] = None):
        """
        保存配置到文件
        
        Args:
            config_file: 配置文件路径，如果为None则使用初始化时的文件
        """
        file_path = config_file or self._config_file
        
        if not file_path:
            logger.error("没有指定配置文件路径")
            return
        
        config_path = Path(file_path)
        
        # 确保目录存在
        config_path.parent.mkdir(parents=True, exist_ok=True)
        
        try:
            with open(config_path, 'w', encoding='utf-8') as f:
                if config_path.suffix.lower() in ['.yml', '.yaml']:
                    yaml.dump(self._config, f, default_flow_style=False, allow_unicode=True)
                elif config_path.suffix.lower() == '.json':
                    json.dump(self._config, f, indent=2, ensure_ascii=False)
                else:
                    logger.error(f"不支持的配置文件格式: {config_path.suffix}")
                    return
            
            logger.info(f"配置已保存到: {file_path}")
            
        except Exception as e:
            logger.error(f"保存配置文件失败: {file_path}, 错误: {str(e)}")
    
    def validate_config(self) -> bool:
        """
        验证配置的有效性
        
        Returns:
            配置是否有效
        """
        try:
            # 验证必需的配置项
            required_configs = [
                'app.name',
                'recognition.default_type',
                'cache.enabled',
                'logging.level'
            ]
            
            for config_path in required_configs:
                value = self.get(config_path)
                if value is None:
                    logger.error(f"缺少必需的配置项: {config_path}")
                    return False
            
            # 验证数值范围
            if self.get('cache.ttl', 0) <= 0:
                logger.error("缓存TTL必须大于0")
                return False
            
            if self.get('recognition.max_image_size', 0) <= 0:
                logger.error("最大图像大小必须大于0")
                return False
            
            # 验证日志级别
            valid_log_levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
            log_level = self.get('logging.level', '').upper()
            if log_level not in valid_log_levels:
                logger.error(f"无效的日志级别: {log_level}")
                return False
            
            logger.info("配置验证通过")
            return True
            
        except Exception as e:
            logger.error(f"配置验证失败: {str(e)}")
            return False
    
    def to_dict(self) -> Dict[str, Any]:
        """
        获取完整配置字典
        
        Returns:
            配置字典
        """
        return self._config.copy()


# 全局配置管理器实例
config = ConfigManager()

# 尝试加载配置文件
config_files = [
    'config/config.yaml',
    'config/config.yml',
    'config.yaml',
    'config.yml',
    'config.json'
]

for config_file in config_files:
    if os.path.exists(config_file):
        config.load_config(config_file)
        break
