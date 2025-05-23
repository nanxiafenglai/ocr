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
apply_patches()

class CaptchaRecognizer:
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
            ValueError: 如果验证码类型不支持
            FileNotFoundError: 如果图片文件不存在
        """
        # 检查处理器是否存在
        if captcha_type not in self._processors:
            raise ValueError(f"不支持的验证码类型: {captcha_type}，支持的类型: {list(self._processors.keys())}")

        # 准备图像数据
        img_data = self._prepare_image(image)

        # 使用对应的处理器处理验证码
        processor = self._processors[captcha_type]
        result = processor.process(img_data, **kwargs)

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
