#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
抖音自动回复软件 - 数据库管理模块
实现SQLite数据库的初始化和操作
"""

import sqlite3
import os
import json
from datetime import datetime


class DatabaseManager:
    """数据库管理器"""
    
    def __init__(self, db_path='douyin_auto.db'):
        """初始化数据库管理器
        
        Args:
            db_path: 数据库文件路径
        """
        self.db_path = db_path
        self._init_database()
    
    def _init_database(self):
        """初始化数据库，创建表结构"""
        try:
            # 连接数据库
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # 创建configs表 - 存储用户设置
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS configs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                key TEXT UNIQUE NOT NULL,
                value TEXT,
                description TEXT,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            ''')
            
            # 创建element_fingerprints表 - 存储元素特征
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS element_fingerprints (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                element_type TEXT NOT NULL,
                selector TEXT,
                fingerprint TEXT,  -- JSON格式存储特征
                confidence REAL,
                learned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            ''')
            
            # 创建operation_logs表 - 存储操作日志
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS operation_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                level TEXT NOT NULL,
                message TEXT NOT NULL,
                details TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            ''')
            
            # 提交事务
            conn.commit()
            
            # 初始化默认配置
            self._init_default_configs(cursor)
            
            # 关闭连接
            conn.close()
            
            print(f"数据库初始化成功: {self.db_path}")
            
        except Exception as e:
            print(f"数据库初始化失败: {e}")
    
    def _init_default_configs(self, cursor):
        """初始化默认配置
        
        Args:
            cursor: SQLite游标
        """
        default_configs = [
            ('douyin_url', 'https://www.douyin.com/im', '抖音私信URL'),
            ('check_interval', '30', '检测间隔（秒）'),
            ('reply_content', '您好，我已收到消息，稍后回复您', '回复内容'),
            ('reply_templates', '您好，我已收到消息，稍后回复您|感谢您的关注，有什么可以帮助您的吗？|抱歉，我现在忙，稍后回复您', '回复模板（用|分隔）'),
            ('reply_frequency_limit', '5', '回复频率限制（每分钟）'),
            ('enable_reply_templates', 'False', '启用回复模板'),
            ('enable_smart_retry', 'True', '启用智能重试'),
            ('enable_operation_delay', 'True', '启用操作延迟'),
            ('work_hours', '09:00 - 21:00', '工作时段'),
            ('min_browser_width', '800', '浏览器最小宽度'),
            ('min_browser_height', '500', '浏览器最小高度'),
        ]
        
        for key, value, description in default_configs:
            try:
                cursor.execute(
                    'INSERT OR IGNORE INTO configs (key, value, description) VALUES (?, ?, ?)',
                    (key, value, description)
                )
            except:
                pass
    
    def get_config(self, key, default=None):
        """获取配置值
        
        Args:
            key: 配置键
            default: 默认值
            
        Returns:
            配置值
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('SELECT value FROM configs WHERE key = ?', (key,))
            result = cursor.fetchone()
            conn.close()
            return result[0] if result else default
        except:
            return default
    
    def set_config(self, key, value, description=''):
        """设置配置值
        
        Args:
            key: 配置键
            value: 配置值
            description: 配置描述
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute(
                'INSERT OR REPLACE INTO configs (key, value, description, updated_at) VALUES (?, ?, ?, CURRENT_TIMESTAMP)',
                (key, value, description)
            )
            conn.commit()
            conn.close()
            return True
        except:
            return False
    
    def save_element_fingerprint(self, element_type, selector, fingerprint, confidence=0.0):
        """保存元素特征
        
        Args:
            element_type: 元素类型
            selector: 选择器
            fingerprint: 特征（字典）
            confidence: 置信度
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute(
                'INSERT INTO element_fingerprints (element_type, selector, fingerprint, confidence) VALUES (?, ?, ?, ?)',
                (element_type, selector, json.dumps(fingerprint), confidence)
            )
            conn.commit()
            conn.close()
            return True
        except:
            return False
    
    def get_element_fingerprints(self, element_type=None):
        """获取元素特征
        
        Args:
            element_type: 元素类型（可选）
            
        Returns:
            元素特征列表
        """
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            if element_type:
                cursor.execute('SELECT * FROM element_fingerprints WHERE element_type = ? ORDER BY learned_at DESC', (element_type,))
            else:
                cursor.execute('SELECT * FROM element_fingerprints ORDER BY learned_at DESC')
            
            results = []
            for row in cursor.fetchall():
                results.append({
                    'id': row['id'],
                    'element_type': row['element_type'],
                    'selector': row['selector'],
                    'fingerprint': json.loads(row['fingerprint']) if row['fingerprint'] else {},
                    'confidence': row['confidence'],
                    'learned_at': row['learned_at']
                })
            
            conn.close()
            return results
        except:
            return []
    
    def add_log(self, level, message, details=''):
        """添加操作日志
        
        Args:
            level: 日志级别（INFO, WARNING, ERROR）
            message: 日志消息
            details: 详细信息
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute(
                'INSERT INTO operation_logs (level, message, details) VALUES (?, ?, ?)',
                (level, message, details)
            )
            conn.commit()
            conn.close()
            return True
        except:
            return False
    
    def get_logs(self, limit=100, level=None):
        """获取操作日志
        
        Args:
            limit: 限制数量
            level: 日志级别（可选）
            
        Returns:
            日志列表
        """
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            if level:
                cursor.execute(
                    'SELECT * FROM operation_logs WHERE level = ? ORDER BY created_at DESC LIMIT ?',
                    (level, limit)
                )
            else:
                cursor.execute(
                    'SELECT * FROM operation_logs ORDER BY created_at DESC LIMIT ?',
                    (limit,)
                )
            
            results = []
            for row in cursor.fetchall():
                results.append({
                    'id': row['id'],
                    'level': row['level'],
                    'message': row['message'],
                    'details': row['details'],
                    'created_at': row['created_at']
                })
            
            conn.close()
            return results
        except:
            return []
    
    def clear_logs(self, days=7):
        """清理旧日志
        
        Args:
            days: 保留天数
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute(
                'DELETE FROM operation_logs WHERE created_at < datetime(\'now\', \'-? days\')',
                (days,)
            )
            conn.commit()
            conn.close()
            return True
        except:
            return False
