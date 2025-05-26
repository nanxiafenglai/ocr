#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
验证码识别器核心类
提供统一的接口来识别不同类型的验证码
"""

import os
import ddddocr
from typing import Union, Dict, Any, Optional
from PIL import Image
import io

# 导入并应用ddddocr补丁
from captcha_recognizer.utils.ddddocr_patch import apply_patches
from captcha_recognizer.utils.cache import image_cache, cached_recognition
from captcha_recognizer.utils.errors import (
    handle_exception, UnsupportedCaptchaTypeError, InvalidImageError,
    RecognitionFailedError
)
from captcha_recognizer.utils.logging_config import LoggerMixin, log_function_call
from captcha_recognizer.utils.performance import monitor_performance
from captcha_recognizer.utils.config import config
apply_patches()

class CaptchaRecognizer(LoggerMixin):
    """
    验证码识别器核心类
    支持文字验证码和计算类验证码的识别
    """

    def __init__(self,
                 ocr_kwargs: Dict[str, Any] = None,
                 det_kwargs: Dict[str, Any] = None):
        """
        初始化验证码识别器

        Args:
            ocr_kwargs: ddddocr OCR初始化参数
            det_kwargs: ddddocr检测器初始化参数
        """
        # 从配置获取默认参数
        recognition_config = config.get_section('recognition')
        self.max_image_size = recognition_config.get('max_image_size', 16 * 1024 * 1024)
        self.supported_formats = recognition_config.get('supported_formats', ['png', 'jpg', 'jpeg', 'gif'])
        self.timeout = recognition_config.get('timeout', 30.0)

        # 默认参数
        if ocr_kwargs is None:
            ocr_kwargs = {}
        if det_kwargs is None:
            det_kwargs = {}

        # 初始化OCR引擎
        self.ocr = ddddocr.DdddOcr(**ocr_kwargs)

        # 初始化检测器（如果需要）
        self.det = None
        if det_kwargs:
            self.det = ddddocr.DdddOcr(det=True, **det_kwargs)

        # 注册处理器
        self._processors = {}
        self._register_default_processors()

        self.logger.info(
            "验证码识别器初始化完成",
            extra={
                'max_image_size': self.max_image_size,
                'supported_formats': self.supported_formats,
                'timeout': self.timeout,
                'event_type': 'recognizer_initialized'
            }
        )

    def _register_default_processors(self):
        """注册默认的验证码处理器"""
        # 导入处理器
        from captcha_recognizer.processors.text_processor import TextCaptchaProcessor
        from captcha_recognizer.processors.calculation_processor import CalculationCaptchaProcessor

        # 注册处理器
        self.register_processor('text', TextCaptchaProcessor(self.ocr))
        self.register_processor('calculation', CalculationCaptchaProcessor(self.ocr))

    def register_processor(self, processor_type: str, processor):
        """
        注册验证码处理器

        Args:
            processor_type: 处理器类型名称
            processor: 处理器实例
        """
        self._processors[processor_type] = processor

    @handle_exception
    @log_function_call
    @monitor_performance(include_args=True, log_slow_calls=True, slow_threshold=2.0)
    def recognize(self,
                  image: Union[str, bytes, Image.Image],
                  captcha_type: str = 'text',
                  **kwargs) -> str:
        """
        识别验证码

        Args:
            image: 验证码图片，可以是文件路径、字节数据或PIL图像对象
            captcha_type: 验证码类型，默认为'text'
            **kwargs: 传递给处理器的额外参数

        Returns:
            识别结果字符串

        Raises:
            UnsupportedCaptchaTypeError: 如果验证码类型不支持
            InvalidImageError: 如果图片数据无效
            RecognitionFailedError: 如果识别失败
        """
        # 记录识别请求开始
        self.logger.info(
            "开始验证码识别",
            extra={
                'captcha_type': captcha_type,
                'image_type': type(image).__name__,
                'kwargs': kwargs,
                'event_type': 'recognition_start'
            }
        )

        # 检查处理器是否存在
        if captcha_type not in self._processors:
            self.logger.error(
                "不支持的验证码类型",
                extra={
                    'captcha_type': captcha_type,
                    'supported_types': list(self._processors.keys()),
                    'event_type': 'unsupported_type'
                }
            )
            raise UnsupportedCaptchaTypeError(captcha_type, list(self._processors.keys()))

        # 准备图像数据
        try:
            img_data = self._prepare_image(image)
            self.logger.debug(
                "图像数据准备完成",
                extra={
                    'image_size': len(img_data),
                    'event_type': 'image_prepared'
                }
            )
        except Exception as e:
            self.logger.error(
                "图像数据处理失败",
                extra={
                    'error': str(e),
                    'image_type': type(image).__name__,
                    'event_type': 'image_preparation_failed'
                }
            )
            raise InvalidImageError(f"图像数据处理失败: {str(e)}")

        # 尝试从缓存获取结果
        image_hash = image_cache.get_image_hash(img_data)
        cached_result = image_cache.get(image_hash)

        if cached_result and cached_result.get('captcha_type') == captcha_type:
            # 检查参数是否匹配
            kwargs_hash = hash(str(sorted(kwargs.items())))
            if cached_result.get('kwargs_hash') == kwargs_hash:
                self.logger.info(
                    "缓存命中，返回缓存结果",
                    extra={
                        'image_hash': image_hash,
                        'captcha_type': captcha_type,
                        'event_type': 'cache_hit'
                    }
                )
                return cached_result['result']

        # 缓存未命中，使用对应的处理器处理验证码
        self.logger.info(
            "缓存未命中，开始识别处理",
            extra={
                'image_hash': image_hash,
                'captcha_type': captcha_type,
                'event_type': 'cache_miss'
            }
        )

        try:
            processor = self._processors[captcha_type]
            result = processor.process(img_data, **kwargs)

            if not result:
                self.logger.warning(
                    "识别结果为空",
                    extra={
                        'image_hash': image_hash,
                        'captcha_type': captcha_type,
                        'event_type': 'empty_result'
                    }
                )
                raise RecognitionFailedError("识别结果为空")

        except Exception as e:
            self.logger.error(
                "验证码识别失败",
                extra={
                    'image_hash': image_hash,
                    'captcha_type': captcha_type,
                    'error': str(e),
                    'error_type': type(e).__name__,
                    'event_type': 'recognition_failed'
                }
            )
            if isinstance(e, RecognitionFailedError):
                raise
            raise RecognitionFailedError(f"验证码识别过程中发生错误: {str(e)}")

        # 将结果存入缓存
        cache_entry = {
            'result': result,
            'captcha_type': captcha_type,
            'kwargs_hash': hash(str(sorted(kwargs.items())))
        }
        image_cache.set(image_hash, cache_entry)

        self.logger.info(
            "验证码识别成功",
            extra={
                'image_hash': image_hash,
                'captcha_type': captcha_type,
                'result_length': len(result) if result else 0,
                'event_type': 'recognition_success'
            }
        )

        return result

    def _prepare_image(self, image: Union[str, bytes, Image.Image]) -> bytes:
        """
        准备图像数据

        Args:
            image: 验证码图片，可以是文件路径、字节数据或PIL图像对象

        Returns:
            图像的字节数据
        """
        if isinstance(image, str):
            # 文件路径
            if not os.path.exists(image):
                raise FileNotFoundError(f"图片文件不存在: {image}")
            with open(image, 'rb') as f:
                return f.read()

        elif isinstance(image, Image.Image):
            # PIL图像对象
            img_byte_arr = io.BytesIO()
            image.save(img_byte_arr, format=image.format or 'PNG')
            return img_byte_arr.getvalue()

        elif isinstance(image, bytes):
            # 字节数据
            return image

        else:
            raise TypeError(f"不支持的图像类型: {type(image)}")
