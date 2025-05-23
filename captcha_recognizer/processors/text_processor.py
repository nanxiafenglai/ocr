#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
文字验证码处理器
处理普通的文字验证码
"""

from typing import Union, Dict, Any, Optional


class TextCaptchaProcessor:
    """
    文字验证码处理器
    处理普通的文字验证码，直接返回OCR识别结果
    """
    
    def __init__(self, ocr_engine):
        """
        初始化文字验证码处理器
        
        Args:
            ocr_engine: OCR引擎实例
        """
        self.ocr = ocr_engine
    
    def process(self, image_data: bytes, **kwargs) -> str:
        """
        处理文字验证码
        
        Args:
            image_data: 验证码图片的字节数据
            **kwargs: 额外参数
            
        Returns:
            识别的文字结果
        """
        # 对于文字验证码，直接返回OCR识别结果
        result = self.ocr.classification(image_data)
        
        # 后处理（如果需要）
        result = self._post_process(result, **kwargs)
        
        return result
    
    def _post_process(self, text: str, **kwargs) -> str:
        """
        对识别结果进行后处理
        
        Args:
            text: OCR识别的原始文本
            **kwargs: 额外参数
            
        Returns:
            处理后的文本
        """
        # 获取后处理选项
        remove_spaces = kwargs.get('remove_spaces', True)
        to_lower = kwargs.get('to_lower', False)
        to_upper = kwargs.get('to_upper', False)
        
        # 应用后处理
        if remove_spaces:
            text = text.replace(' ', '')
        
        if to_lower:
            text = text.lower()
        
        if to_upper:
            text = text.upper()
        
        return text
