#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
抖音自动回复软件 - 配置管理器
管理设置的读取、保存和更新，实现界面控件与数据库的实时同步
"""

from core.database import DatabaseManager


class ConfigManager:
    """配置管理器"""
    
    def __init__(self, db_path='douyin_auto.db'):
        """初始化配置管理器
        
        Args:
            db_path: 数据库文件路径
        """
        self.db = DatabaseManager(db_path)
        self._config_cache = {}
        self._widget_bindings = {}
        self._load_configs()
    
    def _load_configs(self):
        """加载所有配置到缓存"""
        # 这里简化实现，实际需要从数据库加载所有配置
        self._config_cache = {
            'douyin_url': self.db.get_config('douyin_url', 'https://www.douyin.com/im'),
            'check_interval': self.db.get_config('check_interval', '30'),
            'reply_content': self.db.get_config('reply_content', '您好，我已收到消息，稍后回复您'),
            'reply_templates': self.db.get_config('reply_templates', '您好，我已收到消息，稍后回复您|感谢您的关注，有什么可以帮助您的吗？|抱歉，我现在忙，稍后回复您'),
            'reply_frequency_limit': self.db.get_config('reply_frequency_limit', '5'),
            'enable_reply_templates': self.db.get_config('enable_reply_templates', 'False') == 'True',
            'enable_smart_retry': self.db.get_config('enable_smart_retry', 'True') == 'True',
            'enable_operation_delay': self.db.get_config('enable_operation_delay', 'True') == 'True',
            'work_hours': self.db.get_config('work_hours', '09:00 - 21:00'),
            'min_browser_width': self.db.get_config('min_browser_width', '800'),
            'min_browser_height': self.db.get_config('min_browser_height', '500'),
        }
    
    def get(self, key, default=None):
        """获取配置值
        
        Args:
            key: 配置键
            default: 默认值
            
        Returns:
            配置值
        """
        return self._config_cache.get(key, default)
    
    def set(self, key, value):
        """设置配置值
        
        Args:
            key: 配置键
            value: 配置值
            
        Returns:
            bool: 是否设置成功
        """
        try:
            # 更新缓存
            self._config_cache[key] = value
            
            # 保存到数据库
            success = self.db.set_config(key, str(value))
            
            # 同步到绑定的控件
            self._sync_to_widgets(key, value)
            
            return success
        except:
            return False
    
    def bind_widget(self, key, widget, sync_func=None):
        """绑定配置到界面控件
        
        Args:
            key: 配置键
            widget: 界面控件
            sync_func: 同步函数（可选）
        """
        self._widget_bindings[key] = {
            'widget': widget,
            'sync_func': sync_func
        }
        
        # 初始同步
        value = self.get(key)
        if value is not None:
            self._sync_to_widget(key, value)
    
    def _sync_to_widget(self, key, value):
        """同步配置值到界面控件
        
        Args:
            key: 配置键
            value: 配置值
        """
        binding = self._widget_bindings.get(key)
        if not binding:
            return
        
        widget = binding['widget']
        sync_func = binding['sync_func']
        
        try:
            if sync_func:
                # 使用自定义同步函数
                sync_func(widget, value)
            else:
                # 根据控件类型自动同步
                widget_type = type(widget).__name__
                
                if widget_type == 'QLineEdit':
                    widget.setText(str(value))
                elif widget_type == 'QTextEdit':
                    widget.setPlainText(str(value))
                elif widget_type == 'QComboBox':
                    # 假设选项是['30秒', '1分钟', '5分钟']
                    if str(value) == '30':
                        widget.setCurrentIndex(0)
                    elif str(value) == '60':
                        widget.setCurrentIndex(1)
                    elif str(value) == '300':
                        widget.setCurrentIndex(2)
                elif widget_type == 'QCheckBox':
                    widget.setChecked(value is True or str(value).lower() == 'true')
                    
        except Exception as e:
            print(f"同步控件失败: {e}")
    
    def sync_from_widgets(self):
        """从界面控件同步配置到数据库
        
        Returns:
            bool: 是否同步成功
        """
        try:
            for key, binding in self._widget_bindings.items():
                widget = binding['widget']
                widget_type = type(widget).__name__
                
                if widget_type == 'QLineEdit':
                    value = widget.text()
                elif widget_type == 'QTextEdit':
                    value = widget.toPlainText()
                elif widget_type == 'QComboBox':
                    # 假设选项是['30秒', '1分钟', '5分钟']
                    index = widget.currentIndex()
                    if index == 0:
                        value = '30'
                    elif index == 1:
                        value = '60'
                    elif index == 2:
                        value = '300'
                    else:
                        value = '30'
                elif widget_type == 'QCheckBox':
                    value = widget.isChecked()
                else:
                    continue
                
                # 更新配置
                self.set(key, value)
            
            return True
        except:
            return False
    
    def get_all_configs(self):
        """获取所有配置
        
        Returns:
            dict: 所有配置
        """
        return self._config_cache.copy()
    
    def update_all_configs(self, configs):
        """更新所有配置
        
        Args:
            configs: 配置字典
            
        Returns:
            bool: 是否更新成功
        """
        try:
            for key, value in configs.items():
                self.set(key, value)
            return True
        except:
            return False
    
    def reload_configs(self):
        """重新加载配置
        
        Returns:
            bool: 是否加载成功
        """
        try:
            self._load_configs()
            
            # 同步到所有绑定的控件
            for key, value in self._config_cache.items():
                self._sync_to_widget(key, value)
            
            return True
        except:
            return False
