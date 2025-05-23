#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
图像处理工具
提供验证码图像预处理和增强功能
"""

import io
from typing import Union, Tuple, Optional
from PIL import Image, ImageFilter, ImageEnhance


def load_image(image_source: Union[str, bytes, Image.Image]) -> Image.Image:
    """
    加载图像
    
    Args:
        image_source: 图像源，可以是文件路径、字节数据或PIL图像对象
        
    Returns:
        PIL图像对象
    """
    if isinstance(image_source, str):
        # 文件路径
        return Image.open(image_source)
    
    elif isinstance(image_source, bytes):
        # 字节数据
        return Image.open(io.BytesIO(image_source))
    
    elif isinstance(image_source, Image.Image):
        # PIL图像对象
        return image_source
    
    else:
        raise TypeError(f"不支持的图像类型: {type(image_source)}")


def to_bytes(image: Image.Image, format: str = 'PNG') -> bytes:
    """
    将PIL图像转换为字节数据
    
    Args:
        image: PIL图像对象
        format: 图像格式，默认为'PNG'
        
    Returns:
        图像的字节数据
    """
    img_byte_arr = io.BytesIO()
    image.save(img_byte_arr, format=format)
    return img_byte_arr.getvalue()


def resize_image(image: Image.Image, 
                 size: Tuple[int, int], 
                 resample: int = Image.LANCZOS) -> Image.Image:
    """
    调整图像大小
    
    Args:
        image: PIL图像对象
        size: 目标尺寸 (宽, 高)
        resample: 重采样方法
        
    Returns:
        调整大小后的图像
    """
    return image.resize(size, resample=resample)


def convert_to_grayscale(image: Image.Image) -> Image.Image:
    """
    将图像转换为灰度
    
    Args:
        image: PIL图像对象
        
    Returns:
        灰度图像
    """
    return image.convert('L')


def apply_threshold(image: Image.Image, 
                    threshold: int = 128) -> Image.Image:
    """
    应用阈值处理（二值化）
    
    Args:
        image: PIL图像对象（应为灰度图像）
        threshold: 阈值（0-255）
        
    Returns:
        二值化后的图像
    """
    # 确保图像是灰度的
    if image.mode != 'L':
        image = convert_to_grayscale(image)
    
    # 应用阈值
    return image.point(lambda x: 255 if x > threshold else 0, mode='1')


def enhance_contrast(image: Image.Image, 
                     factor: float = 2.0) -> Image.Image:
    """
    增强图像对比度
    
    Args:
        image: PIL图像对象
        factor: 对比度增强因子
        
    Returns:
        对比度增强后的图像
    """
    enhancer = ImageEnhance.Contrast(image)
    return enhancer.enhance(factor)


def enhance_sharpness(image: Image.Image, 
                      factor: float = 2.0) -> Image.Image:
    """
    增强图像锐度
    
    Args:
        image: PIL图像对象
        factor: 锐度增强因子
        
    Returns:
        锐度增强后的图像
    """
    enhancer = ImageEnhance.Sharpness(image)
    return enhancer.enhance(factor)


def remove_noise(image: Image.Image, 
                 method: str = 'median', 
                 **kwargs) -> Image.Image:
    """
    去除图像噪点
    
    Args:
        image: PIL图像对象
        method: 去噪方法，可选'median'或'gaussian'
        **kwargs: 额外参数
            - size: 滤波器大小（对于'median'）
            - radius: 高斯模糊半径（对于'gaussian'）
        
    Returns:
        去噪后的图像
    """
    if method == 'median':
        size = kwargs.get('size', 3)
        return image.filter(ImageFilter.MedianFilter(size=size))
    
    elif method == 'gaussian':
        radius = kwargs.get('radius', 1)
        return image.filter(ImageFilter.GaussianBlur(radius=radius))
    
    else:
        raise ValueError(f"不支持的去噪方法: {method}")


def preprocess_captcha(image_source: Union[str, bytes, Image.Image],
                       grayscale: bool = True,
                       enhance_contrast_factor: Optional[float] = 2.0,
                       enhance_sharpness_factor: Optional[float] = 1.5,
                       remove_noise_method: Optional[str] = 'median',
                       threshold: Optional[int] = None) -> bytes:
    """
    预处理验证码图像
    
    Args:
        image_source: 图像源
        grayscale: 是否转换为灰度
        enhance_contrast_factor: 对比度增强因子，None表示不增强
        enhance_sharpness_factor: 锐度增强因子，None表示不增强
        remove_noise_method: 去噪方法，None表示不去噪
        threshold: 二值化阈值，None表示不二值化
        
    Returns:
        预处理后的图像字节数据
    """
    # 加载图像
    image = load_image(image_source)
    
    # 转换为灰度
    if grayscale:
        image = convert_to_grayscale(image)
    
    # 增强对比度
    if enhance_contrast_factor is not None:
        image = enhance_contrast(image, enhance_contrast_factor)
    
    # 增强锐度
    if enhance_sharpness_factor is not None:
        image = enhance_sharpness(image, enhance_sharpness_factor)
    
    # 去噪
    if remove_noise_method is not None:
        image = remove_noise(image, method=remove_noise_method)
    
    # 二值化
    if threshold is not None:
        image = apply_threshold(image, threshold)
    
    # 转换为字节数据
    return to_bytes(image)
