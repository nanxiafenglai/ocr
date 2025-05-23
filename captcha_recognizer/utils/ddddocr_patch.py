#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
ddddocr库的补丁
解决PIL.Image.ANTIALIAS在新版PIL中被移除的问题
"""

import PIL
from PIL import Image
import ddddocr
import functools
import types

def apply_patches():
    """应用所有补丁"""
    patch_pil_antialias()
    patch_ddddocr_classification()

def patch_pil_antialias():
    """
    为PIL.Image添加ANTIALIAS常量
    在新版PIL中，ANTIALIAS被替换为LANCZOS
    """
    if not hasattr(PIL.Image, 'ANTIALIAS'):
        # 使用LANCZOS作为ANTIALIAS的替代
        PIL.Image.ANTIALIAS = PIL.Image.LANCZOS

def patch_ddddocr_classification():
    """
    修补ddddocr的classification方法
    替换其中使用的Image.ANTIALIAS为更安全的调用方式
    """
    original_classification = ddddocr.DdddOcr.classification
    
    @functools.wraps(original_classification)
    def patched_classification(self, img):
        """
        修补后的classification方法
        确保使用正确的重采样方法
        """
        try:
            # 尝试使用原始方法
            return original_classification(self, img)
        except AttributeError as e:
            if 'ANTIALIAS' in str(e):
                # 如果错误是关于ANTIALIAS的，使用我们的补丁版本
                # 这里我们需要重新实现classification方法的核心逻辑
                # 但使用LANCZOS替代ANTIALIAS
                
                # 以下代码基于ddddocr库的实现，但替换了ANTIALIAS
                import numpy as np
                from PIL import Image
                import io
                
                if isinstance(img, str):
                    with open(img, 'rb') as f:
                        img = f.read()
                
                if isinstance(img, bytes):
                    img = Image.open(io.BytesIO(img))
                
                if isinstance(img, Image.Image):
                    # 这里是关键修改：使用LANCZOS替代ANTIALIAS
                    resampling_method = Image.LANCZOS
                    img = img.resize(
                        (int(img.size[0] * (64 / img.size[1])), 64), 
                        resampling_method
                    ).convert('L')
                    img = np.array(img)
                    
                    # 继续处理图像...
                    # 这里我们简化处理，直接调用原始方法的后续部分
                    # 将处理后的图像转回bytes格式
                    img_pil = Image.fromarray(img)
                    img_byte_arr = io.BytesIO()
                    img_pil.save(img_byte_arr, format='PNG')
                    img_byte = img_byte_arr.getvalue()
                    
                    # 重新调用原始方法，但跳过已经处理的部分
                    # 这是一个简化处理，实际上可能需要更复杂的逻辑
                    return self.classification(img_byte)
            
            # 如果是其他错误，继续抛出
            raise
    
    # 替换原始方法
    ddddocr.DdddOcr.classification = patched_classification
