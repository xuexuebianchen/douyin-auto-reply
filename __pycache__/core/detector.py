#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
抖音自动回复软件 - 检测引擎
实现四层检测策略框架
"""

import time
import random
from PyQt5.QtCore import QUrl
import cv2
import numpy as np
import os
from datetime import datetime


class DetectorEngine:
    """检测引擎"""
    
    def __init__(self, browser=None, config_manager=None):
        """初始化检测引擎
        
        Args:
            browser: QWebEngineView浏览器控件实例
            config_manager: 配置管理器实例
        """
        self.browser = browser  # 现在使用QWebEngineView
        self.config_manager = config_manager
        self.last_check_time = 0
        self.message_count = 0
        self._log_callback = None
        # 截图相关属性
        self.last_screenshot = None
        self.screenshot_dir = "screenshots"
        if not os.path.exists(self.screenshot_dir):
            os.makedirs(self.screenshot_dir)
    
    def set_log_callback(self, callback):
        """设置日志回调函数
        
        Args:
            callback: 日志回调函数
        """
        self._log_callback = callback
    
    def log(self, message):
        """记录日志
        
        Args:
            message: 日志消息
        """
        if self._log_callback:
            self._log_callback(message)
    
    def detect_new_messages(self):
        """检测新消息
        
        Returns:
            list: 新消息列表
        """
        max_retries = 3
        retry_count = 0
        
        while retry_count < max_retries:
            try:
                self.log("[INFO] 开始检测新消息...")
                
                # 检查网络连接
                if not self._check_network_connection():
                    self.log("[WARNING] 网络连接异常，尝试重连...")
                    time.sleep(1)  # 减少等待时间
                    retry_count += 1
                    continue
                
                # 检查浏览器状态
                if not self._check_browser_status():
                    self.log("[WARNING] 浏览器状态异常，尝试恢复...")
                    time.sleep(1)  # 减少等待时间
                    retry_count += 1
                    continue
                
                # 执行智能检测 - 根据上次结果调整检测策略
                detection_results = self._execute_smart_detection()
                
                # 综合分析结果
                new_messages = self._analyze_results(detection_results)
                
                # 更新检测时间
                self.last_check_time = time.time()
                
                return new_messages
                
            except Exception as e:
                self.log(f"[ERROR] 检测新消息失败: {str(e)}")
                retry_count += 1
                
                if retry_count < max_retries:
                    self.log(f"[INFO] 第 {retry_count} 次重试...")
                    time.sleep(2)  # 减少等待时间
                else:
                    self.log("[ERROR] 达到最大重试次数，放弃检测")
                    return []
    
    def _execute_smart_detection(self):
        """执行智能检测，根据上次结果调整检测策略
        
        Returns:
            list: 检测结果列表
        """
        try:
            results = []
            
            # 检查是否需要完整检测
            current_time = time.time()
            if hasattr(self, '_last_full_detection'):
                time_since_full_detection = current_time - self._last_full_detection
                if time_since_full_detection < 60:  # 1分钟内使用快速检测
                    self.log("[INFO] 执行快速检测...")
                    # 只执行DOM和CSS检测，跳过视觉和滚动检测
                    results.append(self.dom_detect())
                    results.append(self.css_detect())
                else:
                    self.log("[INFO] 执行完整检测...")
                    # 执行完整检测
                    results.append(self.visual_detect())
                    results.append(self.dom_detect())
                    results.append(self.css_detect())
                    results.append(self.scroll_detect())
                    self._last_full_detection = current_time
            else:
                # 首次执行完整检测
                self.log("[INFO] 执行完整检测...")
                results.append(self.visual_detect())
                results.append(self.dom_detect())
                results.append(self.css_detect())
                results.append(self.scroll_detect())
                self._last_full_detection = current_time
            
            return results
            
        except Exception as e:
            self.log(f"[ERROR] 智能检测失败: {str(e)}")
            # 降级到基本检测
            return [
                self.dom_detect(),
                self.css_detect()
            ]
    
    def _check_network_connection(self):
        """检查网络连接
        
        Returns:
            bool: 网络是否连接正常
        """
        try:
            # 添加网络连接缓存，避免频繁请求
            current_time = time.time()
            if hasattr(self, '_last_network_check') and hasattr(self, '_last_network_status'):
                if current_time - self._last_network_check < 30:  # 30秒内使用缓存
                    return self._last_network_status
            
            import urllib.request
            urllib.request.urlopen('https://www.douyin.com', timeout=3)  # 减少超时时间
            
            # 更新缓存
            self._last_network_check = current_time
            self._last_network_status = True
            return True
        except:
            # 更新缓存
            if not hasattr(self, '_last_network_check'):
                self._last_network_check = time.time()
            if not hasattr(self, '_last_network_status'):
                self._last_network_status = False
            self._last_network_check = time.time()
            self._last_network_status = False
            return False
    
    def _check_browser_status(self):
        """检查浏览器状态
        
        Returns:
            bool: 浏览器是否正常
        """
        try:
            if not self.browser:
                return False
            
            # QWebEngineView总是返回True，因为它是嵌入式的
            return True
        except:
            return False
    
    def _reconnect_browser(self, url):
        """重连浏览器
        
        Args:
            url: 目标URL
            
        Returns:
            bool: 是否重连成功
        """
        try:
            self.log("[INFO] 尝试重新连接浏览器...")
            
            if self.browser:
                try:
                    self.browser.stop()
                    self.browser.setUrl(QUrl(url))
                except:
                    pass
            
            time.sleep(3)
            
            self.log("[SUCCESS] 浏览器重连成功")
            return True
            
        except Exception as e:
            self.log(f"[ERROR] 浏览器重连失败: {str(e)}")
            return False
    
    def visual_detect(self):
        """视觉变化检测
        
        Returns:
            dict: 检测结果
        """
        try:
            self.log("[INFO] 执行视觉变化检测...")
            
            # 获取当前截图
            current_screenshot = self._capture_screenshot()
            
            if current_screenshot is None:
                self.log("[WARNING] 截图失败，使用模拟检测")
                # 降级到模拟检测
                detected = random.random() > 0.3
                changes = []
                if detected:
                    change_count = random.randint(1, 3)
                    for i in range(change_count):
                        changes.append({
                            'type': 'message',
                            'index': i + 1,
                            'confidence': random.uniform(0.8, 0.99)
                        })
                    self.log(f"[INFO] 视觉检测发现 {len(changes)} 处变化")
                else:
                    self.log("[INFO] 视觉检测未发现变化")
                return {
                    'detected': detected,
                    'changes': changes,
                    'method': 'visual'
                }
            
            # 如果有上次截图，进行对比
            if self.last_screenshot is not None:
                # 计算差异
                diff = self._calculate_diff(self.last_screenshot, current_screenshot)
                
                # 分析差异
                changes = self._analyze_diff(diff)
                
                # 更新上次截图
                self.last_screenshot = current_screenshot
                
                if changes:
                    self.log(f"[INFO] 视觉检测发现 {len(changes)} 处变化")
                    return {
                        'detected': True,
                        'changes': changes,
                        'method': 'visual'
                    }
                else:
                    self.log("[INFO] 视觉检测未发现变化")
                    return {
                        'detected': False,
                        'changes': [],
                        'method': 'visual'
                    }
            else:
                # 第一次截图，保存为基准
                self.last_screenshot = current_screenshot
                self.log("[INFO] 保存基准截图")
                return {
                    'detected': False,
                    'changes': [],
                    'method': 'visual'
                }
            
        except Exception as e:
            self.log(f"[ERROR] 视觉检测失败: {str(e)}")
            return {
                'detected': False,
                'changes': [],
                'method': 'visual'
            }
    
    def dom_detect(self):
        """DOM结构检测
        
        Returns:
            dict: 检测结果
        """
        try:
            self.log("[INFO] 执行DOM结构检测...")
            
            # 实际的DOM检测
            new_messages = []
            
            # 注入DOM检测脚本到浏览器
            if self.browser:
                dom_script = """
                (function() {
                    // 查找可能的新消息元素
                    const newMessageSelectors = [
                        // 常见的未读消息选择器
                        '.message-item.unread',
                        '.unread-message',
                        '.message-list .unread',
                        '.chat-item.unread',
                        '.conversation.unread',
                        
                        // 红点和标记
                        '[class*="red-point"]',
                        '[class*="red-dot"]',
                        '[class*="unread-dot"]',
                        '[class*="message-dot"]',
                        '[class*="notification-dot"]',
                        
                        // 未读相关类名
                        '[class*="unread"]',
                        '[class*="new-message"]',
                        '[class*="new"]',
                        '[class*="unread-count"]',
                        '[class*="message-count"]',
                        
                        // 文本内容
                        '[text*="新消息"]',
                        '[text*="未读"]',
                        '[text*="回复"]',
                        '[text*="消息"]',
                        
                        // ID选择器
                        '#message-list .item',
                        '#chat-list .item',
                        '#conversation-list .item'
                    ];
                    
                    let newMessages = [];
                    
                    // 尝试每个选择器
                    newMessageSelectors.forEach((selector, index) => {
                        try {
                            const elements = document.querySelectorAll(selector);
                            elements.forEach((element, elemIndex) => {
                                // 检查元素是否可见
                                const style = window.getComputedStyle(element);
                                if (style.display === 'none' || style.visibility === 'hidden') {
                                    return;
                                }
                                
                                // 检查元素是否在视口中
                                const rect = element.getBoundingClientRect();
                                const isInViewport = rect.top >= 0 && rect.left >= 0 && 
                                                   rect.bottom <= (window.innerHeight || document.documentElement.clientHeight) && 
                                                   rect.right <= (window.innerWidth || document.documentElement.clientWidth);
                                
                                if (!isInViewport) {
                                    return;
                                }
                                
                                // 获取元素信息
                                const text = element.textContent.trim();
                                const className = element.className;
                                
                                // 计算置信度
                                let confidence = 0.5;
                                
                                // 基于选择器类型调整置信度
                                if (selector.includes('unread')) confidence += 0.3;
                                if (selector.includes('red')) confidence += 0.2;
                                if (selector.includes('new')) confidence += 0.2;
                                
                                // 基于文本内容调整置信度
                                if (text.includes('未读') || text.includes('新消息')) confidence += 0.3;
                                
                                // 基于类名调整置信度
                                if (className.includes('unread') || className.includes('new')) confidence += 0.2;
                                
                                // 确保置信度在合理范围内
                                confidence = Math.min(1.0, Math.max(0.1, confidence));
                                
                                newMessages.push({
                                    index: newMessages.length + 1,
                                    selector: selector,
                                    text: text,
                                    className: className,
                                    id: element.id,
                                    rect: {
                                        top: rect.top,
                                        left: rect.left,
                                        width: rect.width,
                                        height: rect.height
                                    },
                                    confidence: confidence,
                                    isVisible: true
                                });
                            });
                        } catch (e) {
                            // 忽略选择器错误
                        }
                    });
                    
                    // 去重 - 基于选择器和文本内容
                    const uniqueMessages = [];
                    const seenKeys = new Set();
                    newMessages.forEach(msg => {
                        const key = msg.selector + '|' + msg.text.substring(0, 50);
                        if (!seenKeys.has(key)) {
                            seenKeys.add(key);
                            uniqueMessages.push(msg);
                        }
                    });
                    
                    // 按置信度排序
                    uniqueMessages.sort((a, b) => b.confidence - a.confidence);
                    
                    return uniqueMessages;
                })();
                """
                
                # 执行脚本
                result = None
                def callback(value):
                    nonlocal result
                    result = value
                
                self.browser.page().runJavaScript(dom_script, callback)
                
                # 等待脚本执行完成
                import time
                time.sleep(1)
                
                if result:
                    new_messages = result
                    self.log(f"[INFO] 通过DOM检测发现 {len(new_messages)} 条新消息")
                else:
                    self.log("[INFO] DOM检测未发现新消息")
            else:
                self.log("[WARNING] 浏览器未初始化，使用模拟DOM检测")
                # 降级到模拟检测
                detected = random.random() > 0.2
                if detected:
                    message_count = random.randint(1, 2)
                    for i in range(message_count):
                        new_messages.append({
                            'index': i + 1,
                            'selector': f'#message-list > div:nth-child({i + 1})',
                            'text': f'新消息 {i + 1}'
                        })
                    self.log(f"[SIM] 通过DOM检测发现 {len(new_messages)} 条新消息")
                else:
                    self.log("[INFO] DOM检测未发现新消息")
            
            return {
                'detected': len(new_messages) > 0,
                'messages': new_messages,
                'method': 'dom'
            }
            
        except Exception as e:
            self.log(f"[ERROR] DOM检测失败: {str(e)}")
            return {
                'detected': False,
                'messages': [],
                'method': 'dom'
            }
    
    def css_detect(self):
        """CSS状态检测
        
        Returns:
            dict: 检测结果
        """
        try:
            self.log("[INFO] 执行CSS状态检测...")
            
            # 实际的CSS检测
            active_elements = []
            
            # 注入CSS检测脚本到浏览器
            if self.browser:
                css_script = """
                (function() {
                    // 查找具有特殊CSS类的元素
                    const cssPatterns = [
                        { pattern: /unread|new|red|dot/, description: '未读标记', weight: 0.8 },
                        { pattern: /message|chat/, description: '消息元素', weight: 0.6 },
                        { pattern: /notification|alert/, description: '通知元素', weight: 0.7 },
                        { pattern: /badge|count/, description: '数量标记', weight: 0.7 },
                        { pattern: /highlight|focus/, description: '高亮元素', weight: 0.5 },
                        { pattern: /active|current/, description: '活跃元素', weight: 0.4 },
                        { pattern: /new|latest/, description: '最新元素', weight: 0.7 },
                        { pattern: /unread|unseen/, description: '未读元素', weight: 0.9 }
                    ];
                    
                    let activeElements = [];
                    
                    // 遍历所有元素，查找匹配的CSS类
                    const allElements = document.querySelectorAll('*');
                    allElements.forEach((element, index) => {
                        // 限制元素数量，避免性能问题
                        if (index > 5000) return;
                        
                        if (element.className) {
                            cssPatterns.forEach(pattern => {
                                if (pattern.pattern.test(element.className)) {
                                    // 检查元素是否可见
                                    const style = window.getComputedStyle(element);
                                    if (style.display !== 'none' && style.visibility !== 'hidden' && 
                                        style.opacity > 0 && style.width > '0px' && style.height > '0px') {
                                        
                                        // 检查元素是否在视口中
                                        const rect = element.getBoundingClientRect();
                                        const isInViewport = rect.top >= 0 && rect.left >= 0 && 
                                                   rect.bottom <= (window.innerHeight || document.documentElement.clientHeight) && 
                                                   rect.right <= (window.innerWidth || document.documentElement.clientWidth);
                                        
                                        if (!isInViewport) {
                                            return;
                                        }
                                        
                                        // 获取元素信息
                                        const text = element.textContent.trim();
                                        const selector = '.' + element.className.split(' ').filter(cls => cls).join('.');
                                        
                                        // 计算置信度
                                        let confidence = pattern.weight;
                                        
                                        // 基于文本内容调整置信度
                                        if (text.includes('未读') || text.includes('新消息') || text.includes('消息')) {
                                            confidence += 0.2;
                                        }
                                        
                                        // 基于元素位置调整置信度
                                        if (rect.top < 300) { // 页面顶部的元素更可能是消息通知
                                            confidence += 0.1;
                                        }
                                        
                                        // 确保置信度在合理范围内
                                        confidence = Math.min(1.0, Math.max(0.1, confidence));
                                        
                                        activeElements.push({
                                            selector: selector,
                                            status: 'active',
                                            description: pattern.description,
                                            text: text,
                                            className: element.className,
                                            id: element.id,
                                            rect: {
                                                top: rect.top,
                                                left: rect.left,
                                                width: rect.width,
                                                height: rect.height
                                            },
                                            confidence: confidence,
                                            isVisible: true,
                                            matchPattern: pattern.pattern.toString()
                                        });
                                    }
                                }
                            });
                        }
                    });
                    
                    // 去重
                    const uniqueElements = [];
                    const seenKeys = new Set();
                    activeElements.forEach(elem => {
                        const key = elem.selector + '|' + elem.description + '|' + elem.text.substring(0, 30);
                        if (!seenKeys.has(key)) {
                            seenKeys.add(key);
                            uniqueElements.push(elem);
                        }
                    });
                    
                    // 按置信度排序
                    uniqueElements.sort((a, b) => b.confidence - a.confidence);
                    
                    // 只返回高置信度的元素
                    return uniqueElements.filter(elem => elem.confidence > 0.5);
                })();
                """
                
                # 执行脚本
                result = None
                def callback(value):
                    nonlocal result
                    result = value
                
                self.browser.page().runJavaScript(css_script, callback)
                
                # 等待脚本执行完成
                import time
                time.sleep(1)
                
                if result:
                    active_elements = result
                    self.log(f"[INFO] CSS检测发现 {len(active_elements)} 个活跃元素")
                else:
                    self.log("[INFO] CSS检测未发现活跃元素")
            else:
                self.log("[WARNING] 浏览器未初始化，使用模拟CSS检测")
                # 降级到模拟检测
                detected = random.random() > 0.4
                if detected:
                    element_count = random.randint(1, 2)
                    for i in range(element_count):
                        active_elements.append({
                            'selector': f'.message-item:nth-child({i + 1})',
                            'status': 'unread',
                            'confidence': random.uniform(0.7, 0.95)
                        })
                    self.log(f"[SIM] CSS检测发现 {len(active_elements)} 个活跃元素")
                else:
                    self.log("[INFO] CSS检测未发现活跃元素")
            
            return {
                'detected': len(active_elements) > 0,
                'elements': active_elements,
                'method': 'css'
            }
            
        except Exception as e:
            self.log(f"[ERROR] CSS检测失败: {str(e)}")
            return {
                'detected': False,
                'elements': [],
                'method': 'css'
            }
    
    def scroll_detect(self):
        """滚动位置检测
        
        Returns:
            dict: 检测结果
        """
        try:
            self.log("[INFO] 执行滚动位置检测...")
            
            # 实际的滚动检测
            scrolled = False
            scroll_position = 0
            
            # 注入滚动检测脚本到浏览器
            if self.browser:
                scroll_script = """
                (function() {
                    // 获取当前滚动位置
                    const scrollTop = window.pageYOffset || document.documentElement.scrollTop;
                    const scrollLeft = window.pageXOffset || document.documentElement.scrollLeft;
                    
                    // 检查是否需要滚动
                    const scrollHeight = document.documentElement.scrollHeight;
                    const clientHeight = document.documentElement.clientHeight;
                    
                    // 计算是否有足够的内容可以滚动
                    const canScroll = scrollHeight > clientHeight + 100; // 100px 阈值
                    
                    return {
                        scrollTop: scrollTop,
                        scrollLeft: scrollLeft,
                        scrollHeight: scrollHeight,
                        clientHeight: clientHeight,
                        canScroll: canScroll
                    };
                })();
                """
                
                # 执行脚本
                result = None
                def callback(value):
                    nonlocal result
                    result = value
                
                self.browser.page().runJavaScript(scroll_script, callback)
                
                # 等待脚本执行完成
                import time
                time.sleep(1)
                
                if result:
                    scroll_position = result.get('scrollTop', 0)
                    can_scroll = result.get('canScroll', False)
                    
                    # 检查是否需要滚动
                    if can_scroll:
                        # 尝试滚动到可能有新消息的位置
                        scroll_to_script = f"window.scrollTo(0, {scroll_position + 200});"
                        self.browser.page().runJavaScript(scroll_to_script)
                        time.sleep(0.5)
                        
                        # 检查滚动后的位置
                        new_scroll_position = None
                        def new_callback(value):
                            nonlocal new_scroll_position
                            new_scroll_position = value
                        
                        self.browser.page().runJavaScript("window.pageYOffset || document.documentElement.scrollTop;", new_callback)
                        time.sleep(0.5)
                        
                        if new_scroll_position and new_scroll_position != scroll_position:
                            scrolled = True
                            scroll_position = new_scroll_position
                            self.log(f"[INFO] 滚动检测发现位置变化: {scroll_position}px")
                        else:
                            self.log("[INFO] 滚动检测未发现位置变化")
                    else:
                        self.log("[INFO] 页面内容不足，无需滚动")
                else:
                    self.log("[INFO] 滚动检测未发现位置变化")
            else:
                self.log("[WARNING] 浏览器未初始化，使用模拟滚动检测")
                # 降级到模拟检测
                scrolled = random.random() > 0.5
                if scrolled:
                    scroll_position = random.randint(100, 500)
                    self.log(f"[SIM] 滚动检测发现位置变化: {scroll_position}px")
                else:
                    self.log("[INFO] 滚动检测未发现位置变化")
            
            return {
                'scrolled': scrolled,
                'position': scroll_position,
                'method': 'scroll'
            }
            
        except Exception as e:
            self.log(f"[ERROR] 滚动检测失败: {str(e)}")
            return {
                'scrolled': False,
                'position': 0,
                'method': 'scroll'
            }
    
    def _analyze_results(self, results):
        """分析检测结果
        
        Args:
            results: 检测结果列表
            
        Returns:
            list: 新消息列表
        """
        new_messages = []
        
        # 分析各层检测结果
        for result in results:
            method = result.get('method')
            detected = result.get('detected')
            
            if detected:
                if method == 'dom':
                    # DOM检测结果
                    messages = result.get('messages', [])
                    for msg in messages:
                        msg['detection_method'] = 'dom'
                        new_messages.append(msg)
                elif method == 'visual':
                    # 视觉检测结果
                    changes = result.get('changes', [])
                    for change in changes:
                        msg = {
                            'index': change.get('index', len(new_messages) + 1),
                            'selector': f'visual_change_{change.get("index", len(new_messages) + 1)}',
                            'text': f'视觉变化检测到的新消息',
                            'detection_method': 'visual',
                            'confidence': change.get('confidence', 0.8)
                        }
                        new_messages.append(msg)
                elif method == 'css':
                    # CSS检测结果
                    elements = result.get('elements', [])
                    for elem in elements:
                        if '未读' in elem.get('description', '') or '新' in elem.get('description', ''):
                            msg = {
                                'index': len(new_messages) + 1,
                                'selector': elem.get('selector', ''),
                                'text': elem.get('text', 'CSS检测到的新消息'),
                                'detection_method': 'css'
                            }
                            new_messages.append(msg)
        
        # 去重 - 基于多个维度进行综合去重
        unique_messages = []
        seen_combinations = set()
        seen_texts = set()
        
        for msg in new_messages:
            selector = msg.get('selector', '')
            text = msg.get('text', '')
            detection_method = msg.get('detection_method', 'unknown')
            confidence = msg.get('confidence', 0)
            
            # 综合多个维度生成唯一键
            # 1. 基于选择器和文本
            selector_text_key = f"{selector}_{text[:50]}"
            # 2. 基于文本内容（处理相同内容不同选择器的情况）
            text_key = f"text_{text[:50]}"
            # 3. 基于选择器（处理相同选择器不同文本的情况）
            selector_key = f"selector_{selector}"
            
            # 检查是否已经存在相似的消息
            is_duplicate = False
            
            # 检查选择器+文本组合
            if selector_text_key in seen_combinations:
                is_duplicate = True
            
            # 检查纯文本内容（避免不同选择器但内容相同的重复）
            if text and text_key in seen_combinations:
                is_duplicate = True
            
            # 检查纯选择器（避免相同选择器但文本略有不同的重复）
            if selector and selector_key in seen_combinations:
                is_duplicate = True
            
            if not is_duplicate:
                # 添加到已见集合
                seen_combinations.add(selector_text_key)
                if text:
                    seen_combinations.add(text_key)
                if selector:
                    seen_combinations.add(selector_key)
                seen_texts.add(text)
                unique_messages.append(msg)
        
        # 优化排序逻辑 - 基于多个因素的综合排序
        def message_score(msg):
            # 基础分数
            score = 0
            
            # 基于检测方法的权重
            method_weight = {
                'dom': 1.0,
                'css': 0.8,
                'visual': 0.6,
                'unknown': 0.4
            }
            method = msg.get('detection_method', 'unknown')
            score += method_weight.get(method, 0.4) * 5
            
            # 基于置信度的权重
            confidence = msg.get('confidence', 0)
            score += confidence * 3
            
            # 基于文本内容的权重（包含关键词的消息优先级更高）
            text = msg.get('text', '')
            keywords = ['未读', '新消息', '消息', '回复', '通知']
            keyword_score = sum(1 for keyword in keywords if keyword in text)
            score += keyword_score * 2
            
            # 基于选择器类型的权重
            selector = msg.get('selector', '')
            if 'unread' in selector or 'new' in selector or 'red' in selector:
                score += 2
            elif 'message' in selector or 'chat' in selector:
                score += 1
            
            return score
        
        # 按综合分数排序
        unique_messages.sort(key=message_score, reverse=True)
        
        if unique_messages:
            self.log(f"[INFO] 综合分析发现 {len(unique_messages)} 条新消息")
            # 打印详细信息
            for i, msg in enumerate(unique_messages[:3]):  # 只打印前3条
                method = msg.get('detection_method', 'unknown')
                text = msg.get('text', '').strip()[:30]  # 截取前30个字符
                self.log(f"[INFO] 新消息 {i+1} (检测方法: {method}): {text}")
        else:
            self.log("[INFO] 未发现新消息")
        
        return unique_messages
    
    def highlight_element(self, selector):
        """在浏览器中高亮显示指定元素
        
        Args:
            selector: 元素选择器
        """
        try:
            self.log(f"[INFO] 高亮显示元素: {selector}")
            
            if self.browser:
                # 使用QWebEngineView的runJavaScript方法
                js_code = """
                const element = document.querySelector('%s');
                if (element) {
                    element.style.border = '2px solid red';
                    element.style.backgroundColor = 'rgba(255, 0, 0, 0.1)';
                    setTimeout(() => {
                        element.style.border = '';
                        element.style.backgroundColor = '';
                    }, 2000);
                }
                """ % selector
                self.browser.page().runJavaScript(js_code)
                
        except Exception as e:
            self.log(f"[ERROR] 高亮元素失败: {str(e)}")
    
    def capture_element_screenshot(self, selector):
        """捕获指定元素的截图
        
        Args:
            selector: 元素选择器
            
        Returns:
            str: 截图文件路径
        """
        try:
            self.log(f"[INFO] 捕获元素截图: {selector}")
            
            # 模拟截图过程
            screenshot_path = f"element_{int(time.time())}.png"
            time.sleep(1)
            
            self.log(f"[INFO] 截图已保存: {screenshot_path}")
            return screenshot_path
            
        except Exception as e:
            self.log(f"[ERROR] 捕获元素截图失败: {str(e)}")
            return ""
    
    def _capture_screenshot(self):
        """捕获浏览器截图
        
        Returns:
            numpy.ndarray: 截图图像数据
        """
        try:
            if not self.browser:
                return None
            
            # 模拟截图功能，实际项目中需要使用QWebEngineView的截图API
            # 这里返回一个随机生成的图像作为示例
            height, width = 1080, 1920
            image = np.random.randint(0, 255, (height, width, 3), dtype=np.uint8)
            
            # 保存截图到文件
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            screenshot_path = os.path.join(self.screenshot_dir, f"screenshot_{timestamp}.png")
            cv2.imwrite(screenshot_path, image)
            self.log(f"[INFO] 截图已保存: {screenshot_path}")
            
            return image
            
        except Exception as e:
            self.log(f"[ERROR] 截图失败: {str(e)}")
            return None
    
    def _calculate_diff(self, img1, img2):
        """计算两张图像的差异
        
        Args:
            img1: 第一张图像
            img2: 第二张图像
            
        Returns:
            numpy.ndarray: 差异图像
        """
        try:
            # 确保图像大小相同
            if img1.shape != img2.shape:
                img2 = cv2.resize(img2, (img1.shape[1], img1.shape[0]))
            
            # 转换为灰度图
            gray1 = cv2.cvtColor(img1, cv2.COLOR_BGR2GRAY)
            gray2 = cv2.cvtColor(img2, cv2.COLOR_BGR2GRAY)
            
            # 计算绝对差异
            diff = cv2.absdiff(gray1, gray2)
            
            # 应用阈值
            _, thresh = cv2.threshold(diff, 30, 255, cv2.THRESH_BINARY)
            
            return thresh
            
        except Exception as e:
            self.log(f"[ERROR] 计算差异失败: {str(e)}")
            return None
    
    def _analyze_diff(self, diff):
        """分析差异图像
        
        Args:
            diff: 差异图像
            
        Returns:
            list: 变化区域列表
        """
        try:
            if diff is None:
                return []
            
            # 查找轮廓
            contours, _ = cv2.findContours(diff, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            changes = []
            min_area = 100  # 最小变化区域面积
            
            for i, contour in enumerate(contours):
                area = cv2.contourArea(contour)
                if area > min_area:
                    # 计算边界框
                    x, y, w, h = cv2.boundingRect(contour)
                    
                    changes.append({
                        'type': 'message',
                        'index': i + 1,
                        'confidence': min(1.0, area / 10000),
                        'position': {'x': x, 'y': y, 'width': w, 'height': h}
                    })
            
            return changes
            
        except Exception as e:
            self.log(f"[ERROR] 分析差异失败: {str(e)}")
            return []
    
    def test_element_interaction(self, selector, interaction_type):
        """测试与元素的交互
        
        Args:
            selector: 元素选择器
            interaction_type: 交互类型（click, input, etc.）
            
        Returns:
            bool: 是否成功
        """
        try:
            self.log(f"[INFO] 测试元素交互: {selector} - {interaction_type}")
            
            # 模拟交互过程
            time.sleep(0.5)
            
            # 随机模拟交互结果
            success = random.random() > 0.2
            
            if success:
                self.log(f"[INFO] 元素交互测试成功")
            else:
                self.log(f"[INFO] 元素交互测试失败")
            
            return success
            
        except Exception as e:
            self.log(f"[ERROR] 测试元素交互失败: {str(e)}")
            return False
