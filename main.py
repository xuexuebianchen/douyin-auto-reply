#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
抖音自动回复软件 - 主程序入口
批次二：核心智能检测逻辑集成
"""

import sys
import time
import random
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QLineEdit, QTextEdit, QComboBox, QCheckBox,
    QGroupBox, QSplitter, QPlainTextEdit, QDialog, QRadioButton, QButtonGroup,
    QSpinBox
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QUrl
from PyQt5.QtWebEngineWidgets import QWebEngineView

# 导入数据库和配置管理
from core.database import DatabaseManager
from utils.config_manager import ConfigManager
from core.detector import DetectorEngine


class ErrorCorrectionDialog(QDialog):
    """错误纠正对话框"""
    
    # 信号定义
    correction_completed = pyqtSignal(str, str)  # (错误类型, 纠正方式)
    
    def __init__(self, parent=None, error_type="", error_message=""):
        """初始化错误纠正对话框
        
        Args:
            parent: 父窗口
            error_type: 错误类型
            error_message: 错误消息
        """
        super().__init__(parent)
        self.setWindowTitle("智能错误纠正")
        self.setMinimumWidth(400)
        self.setModal(True)
        
        self.error_type = error_type
        self.error_message = error_message
        self.correction_method = ""
        
        self._init_ui()
    
    def _init_ui(self):
        """初始化界面"""
        layout = QVBoxLayout(self)
        
        # 错误信息
        error_group = QGroupBox("错误信息")
        error_layout = QVBoxLayout(error_group)
        
        error_label = QLabel(f"⚠️ 检测到错误：{self.error_message}")
        error_label.setWordWrap(True)
        error_layout.addWidget(error_label)
        
        # 可能的原因
        reason_group = QGroupBox("可能的原因")
        reason_layout = QVBoxLayout(reason_group)
        
        reasons = [
            "页面布局已变化",
            "元素被遮挡",
            "网络加载延迟",
            "元素定位失败"
        ]
        
        for reason in reasons:
            checkbox = QCheckBox(reason)
            reason_layout.addWidget(checkbox)
        
        # 纠正方式
        correction_group = QGroupBox("请选择纠正方式")
        correction_layout = QVBoxLayout(correction_group)
        
        self.correction_buttons = QButtonGroup(self)
        
        correction_methods = [
            (0, "auto_detect", "自动重新检测（推荐）"),
            (1, "relearn", "手动重新学习元素"),
            (2, "skip", "跳过此步骤继续"),
            (3, "pause", "暂停并等待我的操作"),
            (4, "refresh", "刷新页面后重试"),
            (5, "reconnect", "重新连接网络后重试"),
            (6, "reset", "重置所有学习数据")
        ]
        
        self.method_id_map = {}
        for id_int, method_id, method_name in correction_methods:
            radio_btn = QRadioButton(method_name)
            self.correction_buttons.addButton(radio_btn, id_int)
            self.method_id_map[id_int] = method_id
            correction_layout.addWidget(radio_btn)
        
        # 默认选择自动重新检测
        self.correction_buttons.button(0).setChecked(True)
        
        # 按钮
        button_layout = QHBoxLayout()
        
        self.btn_correct = QPushButton("立即纠正")
        self.btn_correct.clicked.connect(self._on_correct)
        
        self.btn_ignore = QPushButton("忽略本次")
        self.btn_ignore.clicked.connect(self._on_ignore)
        
        self.btn_config = QPushButton("修改配置")
        self.btn_config.clicked.connect(self._on_config)
        
        button_layout.addWidget(self.btn_correct)
        button_layout.addWidget(self.btn_ignore)
        button_layout.addWidget(self.btn_config)
        
        # 添加到主布局
        layout.addWidget(error_group)
        layout.addWidget(reason_group)
        layout.addWidget(correction_group)
        layout.addLayout(button_layout)
    
    def _on_correct(self):
        """立即纠正"""
        checked_btn = self.correction_buttons.checkedButton()
        if checked_btn:
            button_id = self.correction_buttons.id(checked_btn)
            self.correction_method = self.method_id_map.get(button_id, "auto_detect")
            self.correction_completed.emit(self.error_type, self.correction_method)
            self.accept()
    
    def _on_ignore(self):
        """忽略本次"""
        self.correction_method = "ignore"
        self.correction_completed.emit(self.error_type, self.correction_method)
        self.accept()
    
    def _on_config(self):
        """修改配置"""
        self.correction_method = "config"
        self.correction_completed.emit(self.error_type, self.correction_method)
        self.accept()


class DetectionThread(QThread):
    """检测线程"""
    
    # 信号定义
    detection_completed = pyqtSignal(list)
    log_message = pyqtSignal(str)
    operation_completed = pyqtSignal(str)
    error_occurred = pyqtSignal(str, str)  # (错误类型, 错误消息)
    
    def __init__(self, detector, interval=3, browser=None, config_manager=None):
        """初始化检测线程
        
        Args:
            detector: 检测引擎
            interval: 检测间隔（秒）
            browser: 浏览器控件
            config_manager: 配置管理器
        """
        super().__init__()
        self.detector = detector
        self.interval = interval
        self.browser = browser
        self.config_manager = config_manager
        self.running = False
        self.paused = False
        self.learning_elements = {}
        self._load_learning_elements()
    
    def _load_learning_elements(self):
        """加载学习到的元素"""
        try:
            if self.config_manager:
                steps = ["私信按钮", "新消息提示", "输入框", "发送按钮"]
                for element_name in steps:
                    key = f'learning_{element_name}'
                    element_info_str = self.config_manager.get(key, '')
                    if element_info_str:
                        import json
                        try:
                            element_info = json.loads(element_info_str)
                            self.learning_elements[element_name] = element_info
                            self.log_message.emit(f"[INFO] 加载 {element_name} 元素信息")
                        except json.JSONDecodeError:
                            self.log_message.emit(f"[ERROR] 解析 {element_name} 元素信息失败")
        except Exception as e:
            self.log_message.emit(f"[ERROR] 加载学习元素失败: {str(e)}")
    
    def run(self):
        """线程运行函数"""
        self.running = True
        self.log_message.emit(f"[INFO] 检测线程已启动，间隔 {self.interval} 秒")
        
        while self.running:
            if not self.paused:
                try:
                    # 执行自动化操作流程
                    self._execute_automation_flow()
                    
                    # 随机化检测间隔（3±1秒）
                    random_interval = self.interval + random.randint(-1, 1)
                    random_interval = max(2, random_interval)  # 最小2秒
                    
                    self.log_message.emit(f"[INFO] 等待 {random_interval} 秒后再次操作")
                    
                    # 等待下一次操作
                    for i in range(random_interval):
                        if not self.running:
                            break
                        time.sleep(1)
                        
                except Exception as e:
                    error_msg = f"[ERROR] 检测线程错误: {str(e)}"
                    self.log_message.emit(error_msg)
                    time.sleep(3)  # 错误后等待3秒
            else:
                time.sleep(1)  # 暂停状态下每秒检查一次
    
    def _execute_automation_flow(self):
        """执行自动化操作流程"""
        try:
            # 步骤1：点击私信按钮
            if self._click_private_message_button():
                self.log_message.emit("[INFO] 点击私信按钮成功")
                
                # 等待页面加载
                time.sleep(1)
                
                # 步骤2：检测新消息
                if self._detect_new_messages():
                    self.log_message.emit("[INFO] 检测到新消息")
                    
                    # 步骤3：处理新消息
                    self._process_new_messages()
                else:
                    self.log_message.emit("[INFO] 未检测到新消息")
                    
                # 步骤4：返回初始页面
                self._return_to_initial_page()
            else:
                error_msg = "点击私信按钮失败"
                self.log_message.emit(f"[ERROR] {error_msg}")
                self.error_occurred.emit("private_message", error_msg)
                
        except Exception as e:
            error_msg = f"执行自动化流程失败: {str(e)}"
            self.log_message.emit(f"[ERROR] {error_msg}")
            self.error_occurred.emit("automation", error_msg)
    
    def _click_private_message_button(self):
        """点击私信按钮"""
        try:
            if not self.browser:
                return False
            
            # 获取私信按钮元素信息
            private_message_btn = self.learning_elements.get("私信按钮")
            if not private_message_btn:
                self.log_message.emit("[ERROR] 未找到私信按钮元素信息")
                return False
            
            # 点击私信按钮
            xpath = private_message_btn.get('xpath')
            if xpath:
                script = f"""
                var element = document.evaluate('{xpath}', document, null, XPathResult.FIRST_ORDERED_NODE_TYPE, null).singleNodeValue;
                if (element) {{
                    element.click();
                    return true;
                }}
                return false;
                """
                result = self.browser.page().runJavaScript(script)
                return result or False
            
            return False
            
        except Exception as e:
            self.log_message.emit(f"[ERROR] 点击私信按钮失败: {str(e)}")
            return False
    
    def _detect_new_messages(self):
        """检测新消息"""
        try:
            if not self.browser:
                return False
            
            # 获取新消息提示元素信息
            new_message_elem = self.learning_elements.get("新消息提示")
            if not new_message_elem:
                self.log_message.emit("[ERROR] 未找到新消息提示元素信息")
                return False
            
            # 检测新消息
            xpath = new_message_elem.get('xpath')
            if xpath:
                script = f"""
                var element = document.evaluate('{xpath}', document, null, XPathResult.FIRST_ORDERED_NODE_TYPE, null).singleNodeValue;
                return element !== null;
                """
                result = self.browser.page().runJavaScript(script)
                return result or False
            
            # 备用方案：检测红点
            script = """
            var redDots = document.querySelectorAll('[class*="red"], [class*="dot"], [class*="unread"]');
            return redDots.length > 0;
            """
            result = self.browser.page().runJavaScript(script)
            return result or False
            
        except Exception as e:
            self.log_message.emit(f"[ERROR] 检测新消息失败: {str(e)}")
            return False
    
    def _process_new_messages(self):
        """处理新消息"""
        try:
            # 步骤1：点击新消息
            if self._click_new_message():
                self.log_message.emit("[INFO] 点击新消息成功")
                
                # 等待页面加载
                time.sleep(1)
                
                # 步骤2：发送自动回复
                if self._send_auto_reply():
                    self.log_message.emit("[INFO] 自动回复发送成功")
                else:
                    self.log_message.emit("[ERROR] 自动回复发送失败")
            else:
                self.log_message.emit("[ERROR] 点击新消息失败")
                
        except Exception as e:
            self.log_message.emit(f"[ERROR] 处理新消息失败: {str(e)}")
    
    def _click_new_message(self):
        """点击新消息"""
        try:
            if not self.browser:
                return False
            
            # 点击第一个新消息
            script = """
            var newMessages = document.querySelectorAll('[class*="new"], [class*="unread"]');
            if (newMessages.length > 0) {
                newMessages[0].click();
                return true;
            }
            return false;
            """
            result = self.browser.page().runJavaScript(script)
            return result or False
            
        except Exception as e:
            self.log_message.emit(f"[ERROR] 点击新消息失败: {str(e)}")
            return False
    
    def _send_auto_reply(self):
        """发送自动回复"""
        try:
            # 检查回复频率限制
            if not self._check_reply_frequency():
                self.log_message.emit("[WARNING] 回复频率超过限制，跳过本次回复")
                return False
            
            if not self.browser:
                return False
            
            # 获取输入框和发送按钮元素信息
            input_box = self.learning_elements.get("输入框")
            send_button = self.learning_elements.get("发送按钮")
            
            if not input_box or not send_button:
                self.log_message.emit("[ERROR] 未找到输入框或发送按钮元素信息")
                return False
            
            # 获取回复内容
            reply_content = self._get_reply_content()
            
            # 输入回复内容
            input_xpath = input_box.get('xpath')
            if input_xpath:
                script = f"""
                var element = document.evaluate('{input_xpath}', document, null, XPathResult.FIRST_ORDERED_NODE_TYPE, null).singleNodeValue;
                if (element) {{
                    element.value = '{reply_content}';
                    element.dispatchEvent(new Event('input', {{bubbles: true}}));
                    return true;
                }}
                return false;
                """
                result = self.browser.page().runJavaScript(script)
                if not result:
                    return False
            
            # 点击发送按钮
            send_xpath = send_button.get('xpath')
            if send_xpath:
                script = f"""
                var element = document.evaluate('{send_xpath}', document, null, XPathResult.FIRST_ORDERED_NODE_TYPE, null).singleNodeValue;
                if (element) {{
                    element.click();
                    return true;
                }}
                return false;
                """
                result = self.browser.page().runJavaScript(script)
                
                if result:
                    # 记录回复时间
                    self._record_reply_time()
                    
                return result or False
            
            return False
            
        except Exception as e:
            self.log_message.emit(f"[ERROR] 发送自动回复失败: {str(e)}")
            return False
    
    def _get_reply_content(self):
        """获取回复内容，支持回复模板"""
        try:
            # 检查是否启用回复模板
            if self.config_manager.get('enable_reply_templates', False):
                templates_str = self.config_manager.get('reply_templates', '您好，我已收到消息，稍后回复您')
                templates = templates_str.split('|')
                
                if templates and len(templates) > 1:
                    # 随机选择一个模板
                    import random
                    return random.choice(templates).strip()
            
            # 使用默认回复内容
            return self.config_manager.get('reply_content', '您好，我已收到消息，稍后回复您')
            
        except Exception as e:
            self.log_message.emit(f"[ERROR] 获取回复内容失败: {str(e)}")
            return '您好，我已收到消息，稍后回复您'
    
    def _check_reply_frequency(self):
        """检查回复频率是否超过限制"""
        try:
            import time
            current_time = time.time()
            
            # 清理1分钟前的回复记录
            self.reply_times = [t for t in self.reply_times if current_time - t < 60]
            
            # 获取频率限制
            frequency_limit = int(self.config_manager.get('reply_frequency_limit', '5'))
            
            # 检查是否超过限制
            if len(self.reply_times) >= frequency_limit:
                return False
            
            return True
            
        except Exception as e:
            self.log_message.emit(f"[ERROR] 检查回复频率失败: {str(e)}")
            return True  # 出错时默认允许回复
    
    def _record_reply_time(self):
        """记录回复时间"""
        try:
            import time
            current_time = time.time()
            self.reply_times.append(current_time)
            self.reply_count += 1
            self.last_reply_time = current_time
            
        except Exception as e:
            self.log_message.emit(f"[ERROR] 记录回复时间失败: {str(e)}")
    
    def _return_to_initial_page(self):
        """返回初始页面"""
        try:
            if not self.browser:
                return False
            
            # 返回抖音首页
            script = """
            window.location.href = 'https://www.douyin.com';
            return true;
            """
            result = self.browser.page().runJavaScript(script)
            return result or False
            
        except Exception as e:
            self.log_message.emit(f"[ERROR] 返回初始页面失败: {str(e)}")
            return False
    
    def stop(self):
        """停止检测线程"""
        self.running = False
    
    def pause(self, paused):
        """暂停/恢复检测线程
        
        Args:
            paused: 是否暂停
        """
        self.paused = paused


class BrowserManager:
    """浏览器管理器"""
    
    def __init__(self, parent_widget):
        """初始化浏览器管理器
        
        Args:
            parent_widget: 父窗口控件
        """
        self.parent_widget = parent_widget
        self.browser = None
        self.status = "ready"
    
    def init_browser(self):
        """初始化浏览器控件
        
        Returns:
            QWebEngineView: 浏览器控件
        """
        # 检查是否已存在浏览器实例
        if self.browser:
            return self.browser
        
        # 创建浏览器控件
        self.browser = QWebEngineView()
        self.browser.setMinimumSize(800, 500)
        
        # 优化浏览器设置，减少资源占用
        # 由于当前PyQt5版本限制，暂时不设置WebEngineSettings
        
        # 优化UA设置
        profile = self.browser.page().profile()
        profile.setHttpUserAgent(
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        )
        
        # 清理缓存
        profile.clearHttpCache()
        
        # 连接信号槽
        self.browser.loadStarted.connect(self._on_load_started)
        self.browser.loadFinished.connect(self._on_load_finished)
        
        self.status = "initialized"
        return self.browser
    
    def navigate(self, url):
        """导航到指定URL
        
        Args:
            url: 目标URL
        """
        if self.browser:
            self.status = "loading"
            self.browser.setUrl(QUrl(url))
    
    def stop(self):
        """停止浏览器
        """
        if self.browser:
            try:
                self.browser.stop()
                self.status = "stopped"
            except:
                pass
    
    def reload(self):
        """重新加载页面
        """
        if self.browser:
            self.browser.reload()
    
    def _on_load_started(self):
        """页面开始加载
        """
        self.status = "loading"
        if hasattr(self.parent_widget, '_add_log'):
            self.parent_widget._add_log("[INFO] 页面开始加载...")
    
    def _on_load_finished(self, ok):
        """页面加载完成
        
        Args:
            ok: 是否加载成功
        """
        if ok:
            self.status = "loaded"
            if hasattr(self.parent_widget, '_add_log'):
                self.parent_widget._add_log("[INFO] 页面加载完成")
                self.parent_widget._on_browser_ready(int(self.parent_widget.config_manager.get('check_interval', '30')))
        else:
            self.status = "error"
            if hasattr(self.parent_widget, '_add_log'):
                self.parent_widget._add_log("[ERROR] 页面加载失败")
    
    def _on_load_error(self, error_code, error_string, url_string, is_ssl_error):
        """页面加载错误
        
        Args:
            error_code: 错误代码
            error_string: 错误信息
            url_string: URL
            is_ssl_error: 是否SSL错误
        """
        self.status = "error"
        if hasattr(self.parent_widget, '_add_log'):
            error_msg = f"[ERROR] 页面加载错误: {error_string}"
            self.parent_widget._add_log(error_msg)
            self.parent_widget._on_browser_error(error_string)


class DouyinAutoReplyApp(QMainWindow):
    """抖音自动回复软件主窗口"""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("抖音自动回复助手")
        self.setGeometry(100, 100, 1200, 800)
        self.setMinimumSize(1050, 700)  # 设置窗口最小尺寸
        
        # 初始化数据库和配置管理
        self.db_manager = DatabaseManager()
        self.config_manager = ConfigManager()
        
        # 浏览器管理器
        self.browser_manager = None
        self.is_monitoring = False
        self.is_paused = False
        
        # 检测引擎和线程管理
        self.detector = None
        self.detection_thread = None
        
        # 浏览器控件
        self.browser_view = None
        
        # 回复统计（用于频率限制）
        self.reply_count = 0
        self.last_reply_time = 0
        self.reply_times = []
        
        # 错误历史记录（用于防止重复弹窗）
        self.error_history = {}
        
        # 创建主布局
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.main_layout = QVBoxLayout(self.central_widget)
        
        # 创建四区域布局
        self._create_top_control_bar()     # 顶部控制栏
        self._create_main_content()        # 中间内容区域（左侧设置 + 中央监控）
        self._create_bottom_log_panel()    # 底部日志面板
        
        # 绑定配置到界面控件
        self._bind_configs()
        
        # 设置默认值
        self._set_default_values()
        
        # 连接信号槽
        self._connect_signals()
    
    def _create_top_control_bar(self):
        """创建顶部控制栏"""
        control_bar = QWidget()
        control_bar.setFixedHeight(50)
        control_layout = QHBoxLayout(control_bar)
        control_layout.setContentsMargins(10, 5, 10, 5)
        
        # 创建控制按钮
        self.btn_start = QPushButton("开始监控")
        self.btn_stop = QPushButton("停止")
        self.btn_pause = QPushButton("暂停")
        self.btn_learning = QPushButton("学习模式")
        self.btn_settings = QPushButton("设置")
        
        # 添加按钮到布局
        buttons = [self.btn_start, self.btn_stop, self.btn_pause, self.btn_learning, self.btn_settings]
        for btn in buttons:
            control_layout.addWidget(btn)
            btn.setFixedHeight(36)
        
        control_layout.addStretch()
        self.main_layout.addWidget(control_bar)
    
    def _create_main_content(self):
        """创建中间内容区域"""
        # 使用QSplitter实现可调整的布局
        main_splitter = QSplitter(Qt.Horizontal)
        main_splitter.setChildrenCollapsible(False)
        
        # 创建左侧设置面板
        settings_widget = QWidget()
        settings_widget.setMinimumWidth(250)
        settings_widget.setMaximumWidth(400)
        
        # 创建滚动区域，确保设置内容过多时可以滚动
        from PyQt5.QtWidgets import QScrollArea
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        
        settings_panel = QWidget()
        settings_layout = QVBoxLayout(settings_panel)
        settings_layout.setContentsMargins(10, 10, 10, 10)
        
        # 添加设置面板内容
        self._create_left_settings_panel(settings_layout)
        
        scroll_area.setWidget(settings_panel)
        
        # 创建中央监控区域
        monitor_area = QWidget()
        monitor_layout = QVBoxLayout(monitor_area)
        monitor_area.setMinimumWidth(800)  # 设置中央区域最小宽度
        
        # 添加监控区域内容
        self._create_central_monitor_area(monitor_layout)
        
        # 添加到splitter
        main_splitter.addWidget(scroll_area)
        main_splitter.addWidget(monitor_area)
        
        # 设置初始大小
        main_splitter.setSizes([250, 950])
        
        self.main_layout.addWidget(main_splitter)
    
    def _create_left_settings_panel(self, parent_layout):
        """创建左侧设置面板"""
        from PyQt5.QtWidgets import QScrollArea, QToolBox, QWidget, QVBoxLayout
        
        # 创建滚动区域
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        
        # 使用QToolBox实现可折叠面板
        tool_box = QToolBox()
        
        # 基础设置面板
        basic_page = QWidget()
        basic_layout = QVBoxLayout(basic_page)
        basic_layout.setContentsMargins(10, 10, 10, 10)
        
        # 抖音私信URL
        url_layout = QHBoxLayout()
        url_label = QLabel("URL：")
        url_label.setFixedWidth(40)
        self.url_input = QLineEdit()
        self.url_input.setText(self.config_manager.get('douyin_url', 'https://www.douyin.com'))
        self.save_url_btn = QPushButton("保存")
        self.save_url_btn.setFixedWidth(60)
        self.save_url_btn.clicked.connect(self._save_url)
        url_layout.addWidget(url_label)
        url_layout.addWidget(self.url_input)
        url_layout.addWidget(self.save_url_btn)
        basic_layout.addLayout(url_layout)
        
        # 检测间隔
        interval_layout = QHBoxLayout()
        interval_label = QLabel("间隔：")
        interval_label.setFixedWidth(40)
        self.interval_combo = QComboBox()
        self.interval_combo.addItems(["30秒", "1分钟", "5分钟"])
        self.interval_combo.setFixedWidth(120)
        interval_layout.addWidget(interval_label)
        interval_layout.addWidget(self.interval_combo)
        interval_layout.addStretch()
        basic_layout.addLayout(interval_layout)
        
        # 回复内容
        reply_layout = QVBoxLayout()
        reply_label = QLabel("回复内容：")
        self.reply_text = QTextEdit()
        self.reply_text.setFixedHeight(60)
        reply_layout.addWidget(reply_label)
        reply_layout.addWidget(self.reply_text)
        basic_layout.addLayout(reply_layout)
        
        # 回复模板
        templates_layout = QVBoxLayout()
        templates_label = QLabel("回复模板（用|分隔）：")
        self.templates_text = QTextEdit()
        self.templates_text.setFixedHeight(80)
        templates_layout.addWidget(templates_label)
        templates_layout.addWidget(self.templates_text)
        basic_layout.addLayout(templates_layout)
        
        # 启用回复模板
        self.enable_templates_check = QCheckBox("启用回复模板")
        basic_layout.addWidget(self.enable_templates_check)
        
        # 回复频率限制
        frequency_layout = QHBoxLayout()
        frequency_label = QLabel("回复频率限制（每分钟）：")
        frequency_label.setFixedWidth(120)
        self.frequency_spin = QSpinBox()
        self.frequency_spin.setRange(1, 30)
        self.frequency_spin.setFixedWidth(80)
        frequency_layout.addWidget(frequency_label)
        frequency_layout.addWidget(self.frequency_spin)
        frequency_layout.addStretch()
        basic_layout.addLayout(frequency_layout)
        
        basic_layout.addStretch()
        tool_box.addItem(basic_page, "基础设置")
        
        # 元素定位设置面板
        element_page = QWidget()
        element_layout = QVBoxLayout(element_page)
        element_layout.setContentsMargins(10, 10, 10, 10)
        
        # 消息列表区域
        msg_list_layout = QHBoxLayout()
        msg_list_label = QLabel("📋 消息列表")
        self.msg_list_status = QLabel("[未学习]")
        self.msg_list_status.setStyleSheet("color: #999; font-size: 12px;")
        self.btn_learn_msg_list = QPushButton("学习")
        self.btn_learn_msg_list.setFixedWidth(60)
        msg_list_layout.addWidget(msg_list_label)
        msg_list_layout.addWidget(self.msg_list_status)
        msg_list_layout.addStretch()
        msg_list_layout.addWidget(self.btn_learn_msg_list)
        element_layout.addLayout(msg_list_layout)
        
        # 新消息提示元素
        new_msg_layout = QHBoxLayout()
        new_msg_label = QLabel("🔴 新消息提示")
        self.new_msg_status = QLabel("[未学习]")
        self.new_msg_status.setStyleSheet("color: #999; font-size: 12px;")
        self.btn_learn_new_msg = QPushButton("学习")
        self.btn_learn_new_msg.setFixedWidth(60)
        new_msg_layout.addWidget(new_msg_label)
        new_msg_layout.addWidget(self.new_msg_status)
        new_msg_layout.addStretch()
        new_msg_layout.addWidget(self.btn_learn_new_msg)
        element_layout.addLayout(new_msg_layout)
        
        # 聊天输入框
        input_layout = QHBoxLayout()
        input_label = QLabel("💬 输入框")
        self.input_status = QLabel("[未学习]")
        self.input_status.setStyleSheet("color: #999; font-size: 12px;")
        self.btn_learn_input = QPushButton("学习")
        self.btn_learn_input.setFixedWidth(60)
        input_layout.addWidget(input_label)
        input_layout.addWidget(self.input_status)
        input_layout.addStretch()
        input_layout.addWidget(self.btn_learn_input)
        element_layout.addLayout(input_layout)
        
        # 发送按钮
        send_layout = QHBoxLayout()
        send_label = QLabel("📤 发送按钮")
        self.send_status = QLabel("[未学习]")
        self.send_status.setStyleSheet("color: #999; font-size: 12px;")
        self.btn_learn_send = QPushButton("学习")
        self.btn_learn_send.setFixedWidth(60)
        send_layout.addWidget(send_label)
        send_layout.addWidget(self.send_status)
        send_layout.addStretch()
        send_layout.addWidget(self.btn_learn_send)
        element_layout.addLayout(send_layout)
        
        element_layout.addStretch()
        tool_box.addItem(element_page, "元素定位设置")
        
        # 高级设置面板
        advanced_page = QWidget()
        advanced_layout = QVBoxLayout(advanced_page)
        advanced_layout.setContentsMargins(10, 10, 10, 10)
        
        # 启用智能重试
        self.retry_check = QCheckBox("智能重试")
        advanced_layout.addWidget(self.retry_check)
        
        # 启用操作延迟
        self.delay_check = QCheckBox("操作延迟")
        advanced_layout.addWidget(self.delay_check)
        
        # 工作时段
        worktime_layout = QHBoxLayout()
        worktime_label = QLabel("工作时段：")
        worktime_label.setFixedWidth(70)
        self.worktime_input = QLineEdit("09:00 - 21:00")
        self.worktime_input.setFixedWidth(120)
        worktime_layout.addWidget(worktime_label)
        worktime_layout.addWidget(self.worktime_input)
        worktime_layout.addStretch()
        advanced_layout.addLayout(worktime_layout)
        
        advanced_layout.addStretch()
        tool_box.addItem(advanced_page, "高级设置")
        
        # 默认选中第一个面板
        tool_box.setCurrentIndex(0)
        
        scroll_area.setWidget(tool_box)
        parent_layout.addWidget(scroll_area)
    
    def _create_central_monitor_area(self, parent_layout):
        """创建中央监控区域"""
        # 使用QSplitter实现垂直可调整布局
        vertical_splitter = QSplitter(Qt.Vertical)
        vertical_splitter.setChildrenCollapsible(False)
        
        # 实时预览（浏览器预览占位）
        preview_group = QGroupBox("实时预览（嵌入浏览器控件）")
        preview_layout = QVBoxLayout(preview_group)
        preview_layout.setContentsMargins(10, 10, 10, 10)
        
        # 创建滚动区域
        from PyQt5.QtWidgets import QScrollArea
        browser_scroll = QScrollArea()
        browser_scroll.setWidgetResizable(True)
        browser_scroll.setMinimumSize(800, 500)  # 设置最小尺寸
        
        # 创建浏览器容器
        self.browser_container = QWidget()
        self.browser_container.setStyleSheet(
            "background-color: #f0f0f0; border: 1px solid #ddd;"
        )
        self.browser_layout = QVBoxLayout(self.browser_container)
        self.browser_layout.setContentsMargins(0, 0, 0, 0)
        
        # 初始占位符
        placeholder_label = QLabel("浏览器预览区域")
        placeholder_label.setAlignment(Qt.AlignCenter)
        self.browser_layout.addWidget(placeholder_label)
        
        # 将浏览器容器放入滚动区域
        browser_scroll.setWidget(self.browser_container)
        preview_layout.addWidget(browser_scroll)
        
        # 操作指示器说明
        indicator_group = QGroupBox("操作指示器")
        indicator_group.setCheckable(True)
        indicator_group.setChecked(False)  # 默认折叠
        indicator_layout = QVBoxLayout(indicator_group)
        indicator_layout.setContentsMargins(10, 10, 10, 10)
        
        indicator_detail = QLabel("● 红色圆圈：正在检测的元素 | ● 绿色高亮：即将点击的元素 | ● 蓝色框：识别到的消息区域")
        indicator_detail.setStyleSheet("font-size: 12px; color: #666;")
        indicator_detail.setWordWrap(True)
        
        indicator_layout.addWidget(indicator_detail)
        
        # 添加到垂直splitter
        vertical_splitter.addWidget(preview_group)
        vertical_splitter.addWidget(indicator_group)
        
        # 设置初始大小
        vertical_splitter.setSizes([500, 80])  # 预览区域500px，指示器80px
        
        parent_layout.addWidget(vertical_splitter)
    
    def _create_bottom_log_panel(self):
        """创建底部日志面板"""
        log_panel = QWidget()
        log_panel.setFixedHeight(200)
        log_layout = QVBoxLayout(log_panel)
        
        log_label = QLabel("操作日志：")
        self.log_text = QPlainTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setStyleSheet(
            "background-color: #f8f8f8; font-family: Consolas, monospace; font-size: 12px;"
        )
        
        # 添加示例日志
        self._add_sample_logs()
        
        log_layout.addWidget(log_label)
        log_layout.addWidget(self.log_text)
        
        self.main_layout.addWidget(log_panel)
    
    def _add_sample_logs(self):
        """添加示例日志"""
        sample_logs = [
            "[14:30:05] ✅ 已连接到抖音页面",
            "[14:30:10] 🔍 正在检测新消息...",
            "[14:30:12] ⚠️ 发现3条新消息",
            "[14:30:15] 👆 点击第1条消息",
            "[14:30:18] 💬 输入回复内容",
            "[14:30:20] 📤 消息已发送",
            "[14:30:22] 🔄 返回消息列表"
        ]
        
        for log in sample_logs:
            self.log_text.appendPlainText(log)
    
    def _bind_configs(self):
        """绑定配置到界面控件"""
        # 绑定基础设置
        self.config_manager.bind_widget('douyin_url', self.url_input)
        self.config_manager.bind_widget('check_interval', self.interval_combo)
        self.config_manager.bind_widget('reply_content', self.reply_text)
        self.config_manager.bind_widget('reply_templates', self.templates_text)
        self.config_manager.bind_widget('reply_frequency_limit', self.frequency_spin)
        self.config_manager.bind_widget('enable_reply_templates', self.enable_templates_check)
        self.config_manager.bind_widget('enable_smart_retry', self.retry_check)
        self.config_manager.bind_widget('enable_operation_delay', self.delay_check)
        self.config_manager.bind_widget('work_hours', self.worktime_input)
    
    def _save_url(self):
        """保存URL设置"""
        url = self.url_input.text().strip()
        if url:
            self.config_manager.set('douyin_url', url)
            self._add_log("[INFO] URL保存成功！")
        else:
            self._add_log("[ERROR] URL不能为空！")
    
    def _set_default_values(self):
        """设置默认值"""
        # 设置URL默认值
        self.url_input.setText(self.config_manager.get('douyin_url', 'https://www.douyin.com'))
        # 这里可以设置其他默认值
        pass
    
    def _connect_signals(self):
        """连接信号槽"""
        # 控制按钮点击事件
        self.btn_start.clicked.connect(self._on_start_monitoring)
        self.btn_stop.clicked.connect(self._on_stop_monitoring)
        self.btn_pause.clicked.connect(self._on_pause_monitoring)
        self.btn_learning.clicked.connect(self._on_learning_mode)
        self.btn_settings.clicked.connect(self._on_settings)
        
        # 界面控件值变化时同步到配置
        self.url_input.textChanged.connect(lambda text: self.config_manager.set('douyin_url', text))
        self.interval_combo.currentIndexChanged.connect(lambda index: self.config_manager.set('check_interval', ['30', '60', '300'][index]))
        self.reply_text.textChanged.connect(lambda: self.config_manager.set('reply_content', self.reply_text.toPlainText()))
        self.templates_text.textChanged.connect(lambda: self.config_manager.set('reply_templates', self.templates_text.toPlainText()))
        self.frequency_spin.valueChanged.connect(lambda value: self.config_manager.set('reply_frequency_limit', str(value)))
        self.enable_templates_check.stateChanged.connect(lambda state: self.config_manager.set('enable_reply_templates', state == Qt.Checked))
        self.retry_check.stateChanged.connect(lambda state: self.config_manager.set('enable_smart_retry', state == Qt.Checked))
        self.delay_check.stateChanged.connect(lambda state: self.config_manager.set('enable_operation_delay', state == Qt.Checked))
        self.worktime_input.textChanged.connect(lambda text: self.config_manager.set('work_hours', text))
    
    def _on_start_monitoring(self):
        """开始监控"""
        if self.is_monitoring:
            self._add_log("[WARNING] 监控已在运行中")
            return
        
        try:
            # 获取配置
            douyin_url = self.config_manager.get('douyin_url', 'https://www.douyin.com/im')
            
            # 初始化浏览器管理器
            self.browser_manager = BrowserManager(self)
            
            # 创建并添加浏览器控件
            if not self.browser_view:
                # 移除占位符
                for i in reversed(range(self.browser_layout.count())):
                    widget = self.browser_layout.itemAt(i).widget()
                    if widget:
                        widget.deleteLater()
                
                # 创建浏览器控件
                self.browser_view = self.browser_manager.init_browser()
                self.browser_layout.addWidget(self.browser_view)
            
            # 导航到抖音私信页面
            self._add_log(f"[INFO] 开始监控抖音私信")
            self._add_log(f"[INFO] 导航到: {douyin_url}")
            self.browser_manager.navigate(douyin_url)
            
            self.is_monitoring = True
            
        except Exception as e:
            self._add_log(f"[ERROR] 启动监控失败: {str(e)}")
    
    def _on_browser_ready(self, check_interval):
        """浏览器准备就绪
        
        Args:
            check_interval: 检测间隔（秒）
        """
        try:
            # 初始化检测引擎
            self.detector = DetectorEngine(
                browser=self.browser_view,  # 现在使用QWebEngineView
                config_manager=self.config_manager
            )
            self.detector.set_log_callback(self._add_log)
            
            # 启动检测线程（传递browser和config_manager参数）
            self.detection_thread = DetectionThread(
                self.detector, 
                interval=3,  # 每隔3秒点击一次私信按钮
                browser=self.browser_view,
                config_manager=self.config_manager
            )
            self.detection_thread.detection_completed.connect(self._on_detection_completed)
            self.detection_thread.log_message.connect(self._add_log)
            self.detection_thread.operation_completed.connect(self._on_operation_completed)
            self.detection_thread.error_occurred.connect(self._on_error_occurred)
            self.detection_thread.start()
            
            self._add_log("[SUCCESS] 浏览器准备就绪，开始检测新消息")
            self._add_log("[INFO] 自动化操作流程已启动，每隔3秒点击一次私信按钮")
            
        except Exception as e:
            self._add_log(f"[ERROR] 初始化检测引擎失败: {str(e)}")
    
    def _on_operation_completed(self, operation):
        """操作完成回调
        
        Args:
            operation: 完成的操作
        """
        self._add_log(f"[INFO] 操作完成: {operation}")
    
    def _on_error_occurred(self, error_type, error_message):
        """错误发生回调
        
        Args:
            error_type: 错误类型
            error_message: 错误消息
        """
        try:
            # 检查是否需要显示错误纠正对话框（避免重复弹窗）
            error_key = f"{error_type}:{error_message[:50]}"  # 使用错误类型和消息前50个字符作为键
            current_time = time.time()
            
            # 检查错误历史
            if error_key in self.error_history:
                last_time, count = self.error_history[error_key]
                # 如果30秒内已经显示过相同错误，或者错误计数超过5次，就不再显示
                if current_time - last_time < 30 or count >= 5:
                    self._add_log(f"[INFO] 错误已处理，跳过重复对话框: {error_type}")
                    return
                # 更新错误历史
                self.error_history[error_key] = (current_time, count + 1)
            else:
                # 新错误，添加到历史
                self.error_history[error_key] = (current_time, 1)
            
            # 清理过期的错误历史（超过1分钟的）
            expired_keys = []
            for key, (timestamp, _) in self.error_history.items():
                if current_time - timestamp > 60:
                    expired_keys.append(key)
            for key in expired_keys:
                del self.error_history[key]
            
            # 显示错误纠正对话框
            dialog = ErrorCorrectionDialog(self, error_type, error_message)
            dialog.correction_completed.connect(self._on_correction_completed)
            dialog.exec_()
        except Exception as e:
            self._add_log(f"[ERROR] 显示错误纠正对话框失败: {str(e)}")
    
    def _on_correction_completed(self, error_type, correction_method):
        """纠正完成回调
        
        Args:
            error_type: 错误类型
            correction_method: 纠正方式
        """
        try:
            self._add_log(f"[INFO] 错误纠正完成: {error_type} - {correction_method}")
            
            # 根据纠正方式执行不同的操作
            if correction_method == "auto_detect":
                # 自动重新检测
                self._add_log("[INFO] 执行自动重新检测")
                # 立即执行一次检测
                if self.detector:
                    self._add_log("[INFO] 立即执行新消息检测")
                    new_messages = self.detector.detect_new_messages()
                    if new_messages:
                        self._add_log(f"[SUCCESS] 重新检测成功，发现 {len(new_messages)} 条新消息")
                    else:
                        self._add_log("[INFO] 重新检测完成，未发现新消息")
                
            elif correction_method == "relearn":
                # 手动重新学习元素
                self._add_log("[INFO] 进入重新学习模式")
                self._on_learning_mode()
                
            elif correction_method == "skip":
                # 跳过此步骤继续
                self._add_log("[INFO] 跳过当前步骤，继续执行")
                
            elif correction_method == "pause":
                # 暂停并等待用户操作
                self._add_log("[INFO] 已暂停，等待用户操作")
                
            elif correction_method == "refresh":
                # 刷新页面后重试
                self._add_log("[INFO] 刷新页面后重试")
                if self.browser_view:
                    self.browser_view.page().reload()
                    time.sleep(3)  # 等待页面刷新
                
            elif correction_method == "reconnect":
                # 重新连接网络后重试
                self._add_log("[INFO] 重新连接网络后重试")
                # 这里可以添加网络重连逻辑
                time.sleep(2)  # 模拟网络重连时间
                
            elif correction_method == "ignore":
                # 忽略本次错误
                self._add_log("[INFO] 忽略本次错误，继续执行")
                
            elif correction_method == "config":
                # 修改配置
                self._add_log("[INFO] 打开配置界面")
                self._on_settings()
                
        except Exception as e:
            self._add_log(f"[ERROR] 处理纠正结果失败: {str(e)}")
    
    def _on_detection_completed(self, new_messages):
        """检测完成处理
        
        Args:
            new_messages: 新消息列表
        """
        if new_messages:
            self._add_log(f"[INFO] 检测到 {len(new_messages)} 条新消息")
            # 这里可以添加自动回复逻辑
        else:
            self._add_log("[INFO] 未检测到新消息")
    
    def _on_stop_monitoring(self):
        """停止监控"""
        if not self.is_monitoring:
            self._add_log("[WARNING] 监控未运行")
            return
        
        try:
            # 停止检测线程
            if self.detection_thread:
                self.detection_thread.stop()
                self.detection_thread.wait()
                self.detection_thread = None
            
            # 停止浏览器
            if self.browser_manager:
                self.browser_manager.stop()
                self.browser_manager = None
            
            # 重置状态
            self.detector = None
            self.is_monitoring = False
            self.is_paused = False
            
            self._add_log("[INFO] 监控已停止")
            
        except Exception as e:
            self._add_log(f"[ERROR] 停止监控失败: {str(e)}")
    
    def _on_pause_monitoring(self):
        """暂停监控"""
        if not self.is_monitoring:
            self._add_log("[WARNING] 监控未运行")
            return
        
        self.is_paused = not self.is_paused
        status = "暂停" if self.is_paused else "恢复"
        
        # 暂停/恢复检测线程
        if self.detection_thread:
            self.detection_thread.pause(self.is_paused)
        
        self._add_log(f"[INFO] 监控已{status}")
    
    def _on_learning_mode(self):
        """学习模式"""
        self._add_log("[INFO] 进入学习模式")
        
        try:
            # 检查浏览器是否已初始化
            if not self.browser_view:
                self._add_log("[ERROR] 浏览器未初始化，请先启动监控")
                return
            
            # 进入学习模式状态
            self.is_learning = True
            
            # 显示学习模式提示
            self._add_log("[INFO] 学习模式已启动，请点击页面上的元素进行学习")
            self._add_log("[INFO] 按顺序学习：1.私信按钮 2.新消息提示 3.输入框 4.发送按钮")
            
            # 初始化学习步骤
            self.learning_step = 0
            self.learning_elements = {}
            
            # 开始学习流程
            self._start_learning_process()
            
        except Exception as e:
            self._add_log(f"[ERROR] 进入学习模式失败: {str(e)}")
            self.is_learning = False
    
    def _start_learning_process(self):
        """开始学习流程"""
        steps = [
            "私信按钮",
            "新消息提示",
            "输入框",
            "发送按钮"
        ]
        
        try:
            if self.learning_step < len(steps):
                current_step = steps[self.learning_step]
                self._add_log(f"[INFO] 请点击页面上的 {current_step}")
                
                # 检查浏览器状态
                if not self.browser_view:
                    self._add_log("[ERROR] 浏览器未初始化，请先启动监控")
                    # 显示错误提示
                    from PyQt5.QtWidgets import QMessageBox
                    msg_box = QMessageBox()
                    msg_box.setWindowTitle("错误")
                    msg_box.setText("浏览器未初始化")
                    msg_box.setInformativeText("请先启动监控，待浏览器准备就绪后再进入学习模式")
                    msg_box.setStandardButtons(QMessageBox.Ok)
                    msg_box.exec_()
                    self.is_learning = False
                    return
                
                # 注入学习模式脚本到浏览器
                try:
                    self._inject_learning_script(current_step)
                except Exception as e:
                    self._add_log(f"[ERROR] 注入学习脚本失败: {str(e)}")
                    # 显示错误提示
                    from PyQt5.QtWidgets import QMessageBox
                    msg_box = QMessageBox()
                    msg_box.setWindowTitle("错误")
                    msg_box.setText("注入学习脚本失败")
                    msg_box.setInformativeText(f"错误信息: {str(e)}")
                    msg_box.setStandardButtons(QMessageBox.Retry | QMessageBox.Cancel)
                    msg_box.setDefaultButton(QMessageBox.Retry)
                    
                    reply = msg_box.exec_()
                    if reply == QMessageBox.Retry:
                        # 重新尝试
                        self._start_learning_process()
                    else:
                        # 取消学习
                        self.is_learning = False
                        self._add_log("[INFO] 学习模式已取消")
            else:
                # 学习完成
                self._add_log("[SUCCESS] 学习模式完成，所有元素已学习")
                self.is_learning = False
                
                # 保存学习结果
                self._save_learning_results()
                
                # 显示学习完成提示
                from PyQt5.QtWidgets import QMessageBox
                msg_box = QMessageBox()
                msg_box.setWindowTitle("学习完成")
                msg_box.setText("学习模式已完成")
                msg_box.setInformativeText("所有元素已成功学习，现在可以开始监控")
                msg_box.setStandardButtons(QMessageBox.Ok)
                msg_box.exec_()
                
        except Exception as e:
            self._add_log(f"[ERROR] 学习流程失败: {str(e)}")
            # 显示错误提示
            from PyQt5.QtWidgets import QMessageBox
            msg_box = QMessageBox()
            msg_box.setWindowTitle("错误")
            msg_box.setText("学习流程失败")
            msg_box.setInformativeText(f"错误信息: {str(e)}")
            msg_box.setStandardButtons(QMessageBox.Retry | QMessageBox.Cancel)
            msg_box.setDefaultButton(QMessageBox.Retry)
            
            reply = msg_box.exec_()
            if reply == QMessageBox.Retry:
                # 重新尝试
                self._start_learning_process()
            else:
                # 取消学习
                self.is_learning = False
                self._add_log("[INFO] 学习模式已取消")
    
    def _inject_learning_script(self, element_name):
        """注入学习模式脚本到浏览器"""
        # 使用普通字符串，避免f-string语法错误
        script = '''
        // 学习模式脚本
        (function() {
            // 全局变量
            window.learningMode = true;
            window.currentElement = 'ELEMENT_NAME';
            window.selectedElement = null;
            
            // 创建覆盖层
            const overlay = document.createElement('div');
            overlay.id = 'learning-overlay';
            overlay.style.position = 'fixed';
            overlay.style.top = '0';
            overlay.style.left = '0';
            overlay.style.width = '100%';
            overlay.style.height = '100%';
            overlay.style.backgroundColor = 'rgba(0, 0, 0, 0.3)';
            overlay.style.zIndex = '9999';
            overlay.style.cursor = 'crosshair';
            
            // 添加提示信息
            const hint = document.createElement('div');
            hint.style.position = 'absolute';
            hint.style.top = '20px';
            hint.style.left = '50%';
            hint.style.transform = 'translateX(-50%)';
            hint.style.backgroundColor = 'rgba(0, 0, 0, 0.8)';
            hint.style.color = 'white';
            hint.style.padding = '10px 20px';
            hint.style.borderRadius = '5px';
            hint.style.fontSize = '16px';
            hint.style.zIndex = '10000';
            hint.textContent = '请点击页面上的 ' + 'ELEMENT_NAME';
            overlay.appendChild(hint);
            
            // 点击事件处理
            overlay.addEventListener('click', function(e) {
                e.stopPropagation();
                e.preventDefault();
                
                try {
                    // 获取点击位置的元素
                    const target = document.elementFromPoint(e.clientX, e.clientY);
                    if (target) {
                        // 保存选中元素
                        window.selectedElement = target;
                        
                        // 高亮显示选中元素
                        target.style.border = '2px solid red';
                        target.style.backgroundColor = 'rgba(255, 0, 0, 0.2)';
                        
                        // 移除覆盖层
                        document.body.removeChild(overlay);
                        
                        // 发送元素信息
                        const rect = target.getBoundingClientRect();
                        const elementInfo = {
                            tagName: target.tagName || 'Unknown',
                            className: target.className || '',
                            id: target.id || '',
                            xpath: getXPath(target),
                            css: getCSSPath(target),
                            text: target.textContent ? target.textContent.trim() : '',
                            rect: {
                                top: rect.top,
                                left: rect.left,
                                width: rect.width,
                                height: rect.height
                            }
                        };
                        return elementInfo;
                    }
                } catch (error) {
                    console.error('学习模式错误:', error);
                    return null;
                }
            });
            
            // 获取XPath
            function getXPath(element) {{
                if (!element) return '';
                if (element.id) return '//*[@id="' + element.id + '"]';
                if (element === document.body) return '/html/body';
                
                let ix = 0;
                let siblings = element.parentNode.childNodes;
                for (let i = 0; i < siblings.length; i++) {{
                    let sibling = siblings[i];
                    if (sibling === element) {{
                        const tagName = element.tagName ? element.tagName.toLowerCase() : 'div';
                        return getXPath(element.parentNode) + '/' + tagName + '[' + (ix + 1) + ']';
                    }}
                    if (sibling.nodeType === 1 && sibling.tagName === element.tagName) {{
                        ix++;
                    }}
                }}
                return '';
            }}
            
            // 获取CSS选择器
            function getCSSPath(element) {{
                if (!element) return '';
                if (element.id) return '#' + element.id;
                if (element === document.body) return 'body';
                
                let path = [];
                while (element.parentNode) {{
                    let tagName = element.tagName ? element.tagName.toLowerCase() : 'div';
                    let className = element.className ? '.' + element.className.split(' ').join('.') : '';
                    path.unshift(tagName + className);
                    element = element.parentNode;
                }}
                return path.join(' > ');
            }}
            
            // 添加覆盖层到页面
            document.body.appendChild(overlay);
        }})();
        '''
        
        # 替换元素名称
        script = script.replace('ELEMENT_NAME', element_name)
        
        # 注入脚本到浏览器
        self.browser_view.page().runJavaScript(script, self._on_element_selected)
    
    def _on_element_selected(self, element_info):
        """元素选择回调"""
        if not element_info:
            self._add_log("[ERROR] 未选择元素")
            return
        
        try:
            # 获取当前学习步骤
            steps = ["私信按钮", "新消息提示", "输入框", "发送按钮"]
            current_step = steps[self.learning_step]
            
            # 显示用户确认对话框
            from PyQt5.QtWidgets import QMessageBox
            
            tag_name = element_info.get('tagName', 'Unknown')
            class_name = element_info.get('className', 'NoClass')
            element_desc = f"{tag_name}.{class_name}"
            
            msg_box = QMessageBox()
            msg_box.setWindowTitle("元素确认")
            msg_box.setText(f"您选择的是 {current_step} 吗？")
            msg_box.setInformativeText(f"元素信息: {element_desc}")
            msg_box.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
            msg_box.setDefaultButton(QMessageBox.Yes)
            
            # 显示对话框并获取用户选择
            reply = msg_box.exec_()
            
            if reply == QMessageBox.Yes:
                # 用户确认选择
                # 保存学习到的元素
                self.learning_elements[current_step] = element_info
                
                # 记录日志
                self._add_log(f"[SUCCESS] 学习到 {current_step}: {element_desc}")
                
                # 测试验证元素
                if self._test_element_interaction(current_step, element_info):
                    self._add_log(f"[SUCCESS] {current_step} 测试通过")
                    # 进入下一步
                    self.learning_step += 1
                    self._start_learning_process()
                else:
                    self._add_log(f"[WARNING] {current_step} 测试失败，建议重新学习")
                    # 重新开始当前步骤
                    self._start_learning_process()
            else:
                # 用户取消选择，重新开始当前步骤
                self._add_log(f"[INFO] 用户取消选择 {current_step}，请重新点击")
                self._start_learning_process()
            
        except Exception as e:
            self._add_log(f"[ERROR] 处理学习元素失败: {str(e)}")
            # 重新开始当前步骤
            self._start_learning_process()
    
    def _validate_saved_element(self, element_name, element_info):
        """验证保存的元素信息
        
        Args:
            element_name: 元素名称
            element_info: 元素信息
            
        Returns:
            bool: 验证是否通过
        """
        try:
            # 检查元素信息的必要属性
            required_fields = ['tagName', 'className', 'xpath', 'css']
            for field in required_fields:
                if field not in element_info:
                    self._add_log(f"[ERROR] {element_name} 缺少必要属性: {field}")
                    return False
            
            # 检查选择器是否有效
            css_selector = element_info.get('css', '')
            xpath_selector = element_info.get('xpath', '')
            
            if not css_selector and not xpath_selector:
                self._add_log(f"[ERROR] {element_name} 无有效选择器")
                return False
            
            # 检查元素类型是否正确
            tag_name = element_info.get('tagName', '').upper()
            if not tag_name:
                self._add_log(f"[ERROR] {element_name} 无标签名")
                return False
            
            return True
            
        except Exception as e:
            self._add_log(f"[ERROR] 验证元素失败: {str(e)}")
            return False
    
    def _test_element_interaction(self, element_type, element_info):
        """测试元素交互
        
        Args:
            element_type: 元素类型
            element_info: 元素信息
            
        Returns:
            bool: 测试是否通过
        """
        try:
            self._add_log(f"[INFO] 测试 {element_type} 交互...")
            
            if not self.browser_view:
                self._add_log("[ERROR] 浏览器未初始化")
                return False
            
            # 获取元素选择器
            selector = element_info.get('css', '')
            if not selector:
                selector = element_info.get('xpath', '')
            
            if not selector:
                self._add_log("[ERROR] 元素无有效选择器")
                return False
            
            # 根据元素类型执行不同的测试
            if element_type in ["私信按钮", "发送按钮"]:
                # 测试点击操作
                test_script = f"""
                (function() {{
                    try {{
                        const element = document.querySelector('{selector}');
                        if (element) {{
                            // 检查元素是否可见
                            const style = window.getComputedStyle(element);
                            const isVisible = style.display !== 'none' && style.visibility !== 'hidden';
                            
                            // 检查元素是否可点击
                            const isClickable = element.clientWidth > 0 && element.clientHeight > 0;
                            
                            return isVisible && isClickable;
                        }}
                        return false;
                    }} catch (e) {{
                        return false;
                    }}
                }})();
                """
            elif element_type == "输入框":
                # 测试输入操作
                test_script = f"""
                (function() {{
                    try {{
                        const element = document.querySelector('{selector}');
                        if (element) {{
                            // 检查元素是否可见
                            const style = window.getComputedStyle(element);
                            const isVisible = style.display !== 'none' && style.visibility !== 'hidden';
                            
                            // 检查元素是否可编辑
                            const isEditable = element.isContentEditable || 
                                             element.tagName === 'INPUT' || 
                                             element.tagName === 'TEXTAREA';
                            
                            return isVisible && isEditable;
                        }}
                        return false;
                    }} catch (e) {{
                        return false;
                    }}
                }})();
                """
            else:
                # 测试元素存在性和可见性
                test_script = f"""
                (function() {{
                    try {{
                        const element = document.querySelector('{selector}');
                        if (element) {{
                            // 检查元素是否可见
                            const style = window.getComputedStyle(element);
                            return style.display !== 'none' && style.visibility !== 'hidden';
                        }}
                        return false;
                    }} catch (e) {{
                        return false;
                    }}
                }})();
                """
            
            # 执行测试脚本
            result = None
            def callback(value):
                nonlocal result
                result = value
            
            self.browser_view.page().runJavaScript(test_script, callback)
            
            # 等待脚本执行完成
            import time
            time.sleep(1)
            
            if result:
                self._add_log(f"[INFO] {element_type} 交互测试通过")
                return True
            else:
                self._add_log(f"[ERROR] {element_type} 交互测试失败")
                return False
            
        except Exception as e:
            self._add_log(f"[ERROR] 测试元素交互失败: {str(e)}")
            return False
    
    def _save_learning_results(self):
        """保存学习结果"""
        try:
            # 保存学习到的元素信息
            for element_name, element_info in self.learning_elements.items():
                import json
                element_info_str = json.dumps(element_info)
                key = f'learning_{element_name}'
                self.config_manager.set(key, element_info_str)
                self._add_log(f"[INFO] 保存 {element_name} 元素信息成功")
            
            # 验证保存的元素信息
            self._add_log("[INFO] 验证保存的元素信息...")
            
            # 测试保存的元素信息
            all_valid = True
            for element_name, element_info in self.learning_elements.items():
                if not self._validate_saved_element(element_name, element_info):
                    all_valid = False
                    self._add_log(f"[WARNING] {element_name} 验证失败")
                else:
                    self._add_log(f"[SUCCESS] {element_name} 验证通过")
            
            # 检查学习结果的完整性
            required_elements = ["私信按钮", "新消息提示", "输入框", "发送按钮"]
            missing_elements = []
            
            for element in required_elements:
                if element not in self.learning_elements:
                    missing_elements.append(element)
            
            if missing_elements:
                self._add_log(f"[ERROR] 学习结果不完整，缺少元素: {', '.join(missing_elements)}")
                
                # 显示错误提示
                from PyQt5.QtWidgets import QMessageBox
                msg_box = QMessageBox()
                msg_box.setWindowTitle("错误")
                msg_box.setText("学习结果不完整")
                msg_box.setInformativeText(f"缺少必要元素: {', '.join(missing_elements)}\n建议重新开始学习模式，确保所有元素都被正确学习")
                msg_box.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
                msg_box.setDefaultButton(QMessageBox.Yes)
                
                reply = msg_box.exec_()
                if reply == QMessageBox.Yes:
                    # 重新开始学习
                    self._add_log("[INFO] 用户选择重新学习")
                    self.learning_step = 0
                    self.learning_elements = {}
                    self._start_learning_process()
                    return
                else:
                    # 继续但显示警告
                    self._add_log("[WARNING] 继续使用不完整的学习结果，可能导致自动化操作失败")
            
            if all_valid:
                self._add_log("[SUCCESS] 所有元素信息验证通过")
            else:
                self._add_log("[WARNING] 部分元素信息验证失败，建议重新学习")
                
                # 显示警告提示
                from PyQt5.QtWidgets import QMessageBox
                msg_box = QMessageBox()
                msg_box.setWindowTitle("警告")
                msg_box.setText("部分元素信息验证失败")
                msg_box.setInformativeText("建议重新学习失败的元素，以确保自动化操作正常运行")
                msg_box.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
                msg_box.setDefaultButton(QMessageBox.No)
                
                reply = msg_box.exec_()
                if reply == QMessageBox.Yes:
                    # 重新开始学习
                    self._add_log("[INFO] 用户选择重新学习")
                    self.learning_step = 0
                    self.learning_elements = {}
                    self._start_learning_process()
                    return
            
            # 更新界面状态
            self.msg_list_status.setText("[已学习]")
            self.msg_list_status.setStyleSheet("color: #4CAF50; font-size: 12px;")
            self.new_msg_status.setText("[已学习]")
            self.new_msg_status.setStyleSheet("color: #4CAF50; font-size: 12px;")
            self.input_status.setText("[已学习]")
            self.input_status.setStyleSheet("color: #4CAF50; font-size: 12px;")
            self.send_status.setText("[已学习]")
            self.send_status.setStyleSheet("color: #4CAF50; font-size: 12px;")
            
        except Exception as e:
            self._add_log(f"[ERROR] 保存学习结果失败: {str(e)}")
            
            # 显示错误提示
            from PyQt5.QtWidgets import QMessageBox
            msg_box = QMessageBox()
            msg_box.setWindowTitle("错误")
            msg_box.setText("保存学习结果失败")
            msg_box.setInformativeText(f"错误信息: {str(e)}")
            msg_box.setStandardButtons(QMessageBox.Ok)
            msg_box.exec_()
    
    def _on_settings(self):
        """设置"""
        self._add_log("[INFO] 打开设置面板")
        # 这里可以添加设置面板的逻辑
    
    def _add_log(self, message):
        """添加日志
        
        Args:
            message: 日志消息
        """
        # 获取当前时间
        current_time = time.strftime("[%H:%M:%S]")
        log_message = f"{current_time} {message}"
        
        # 添加到日志面板
        if hasattr(self, 'log_text'):
            self.log_text.appendPlainText(log_message)
        
        # 打印到控制台
        print(log_message)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = DouyinAutoReplyApp()
    window.show()
    sys.exit(app.exec_())
