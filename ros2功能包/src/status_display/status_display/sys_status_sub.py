# -*- coding: utf-8 -*-
"""
sys_status_sub.py —— 系统状态订阅节点 + PySide2 图形窗口

功能：
    订阅话题 /sys_status（status_interfaces/msg/SystemStatus），
    将收到的采集时间、CPU 使用率、内存使用率、网卡收发数据量及速率
    实时显示在 Qt 窗口中。

ROS2 与 Qt 事件循环如何共存：
    Qt 有自己的事件循环（app.exec_()），rclpy.spin() 也会阻塞等待消息。
    这里用 Qt 的 QTimer 每 100ms 调用一次 rclpy.spin_once()（非阻塞），
    让 ROS2 在 Qt 事件循环的间隙处理消息回调。
    因为回调最终运行在 Qt 主线程里，所以可以直接更新界面控件，无需加锁。

依赖安装：
    sudo apt install python3-pyside2.qtwidgets
"""
import sys
from datetime import datetime

import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy, HistoryPolicy

# PySide2 是 Qt5 的官方 Python 绑定
from PySide2.QtCore import Qt, QTimer
from PySide2.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QFormLayout,
    QGroupBox, QLabel, QProgressBar,
)

from status_interfaces.msg import SystemStatus


def human_bytes(num):
    """把字节数转换成便于阅读的字符串，例如 1536.0 -> '1.50 KB'。"""
    for unit in ('B', 'KB', 'MB', 'GB', 'TB'):
        if abs(num) < 1024.0:
            return '{:.2f} {}'.format(num, unit)
        num /= 1024.0
    return '{:.2f} PB'.format(num)


def human_rate(bytes_per_sec):
    """把“字节/秒”转换成便于阅读的网速字符串，例如 '1.50 MB/s'。"""
    return human_bytes(bytes_per_sec) + '/s'


class SysStatusSub(Node):
    """系统状态订阅者节点：只负责收消息，并交给窗口显示。"""

    def __init__(self):
        super().__init__('sys_status_sub')

        # QoS 必须与发布端兼容（这里与发布端配置完全一致）
        qos_profile = QoSProfile(
            reliability=ReliabilityPolicy.BEST_EFFORT,
            history=HistoryPolicy.KEEP_LAST,
            depth=1,
        )

        # 创建订阅者：消息类型、话题名、回调函数、QoS
        self.subscription_ = self.create_subscription(
            SystemStatus, '/sys_status', self.listener_callback, qos_profile)

        # 窗口对象在 main() 中注入，避免节点类直接依赖界面细节
        self.window = None
        self.received_first_msg = False

    def listener_callback(self, msg):
        """收到一帧消息时被调用（由主线程中的 spin_once 触发）。"""
        # 直接刷新界面
        if self.window is not None:
            self.window.update_status(msg)

        # 只在第一次收到消息时打印一次，避免刷屏
        if not self.received_first_msg:
            self.received_first_msg = True
            self.get_logger().info('已收到第一帧系统状态数据，窗口开始刷新')


class SystemStatusWindow(QWidget):
    """系统状态显示主窗口。"""

    def __init__(self):
        super().__init__()

        # ---------------- 窗口基本属性 ----------------
        self.setWindowTitle('系统状态监视器')
        self.resize(460, 420)

        # 最外层垂直布局
        self.root_layout = QVBoxLayout()

        # ---------------- 1. 采集时间 ----------------
        time_group = QGroupBox('采集时间')
        time_layout = QHBoxLayout()
        self.time_label = QLabel('等待数据...')
        # 字体放大并居中，更醒目
        self.time_label.setAlignment(Qt.AlignCenter)
        self.time_label.setStyleSheet('font-size: 18px; font-weight: bold;')
        time_layout.addWidget(self.time_label)
        time_group.setLayout(time_layout)
        self.root_layout.addWidget(time_group)

        # ---------------- 2. CPU 使用率 ----------------
        cpu_group = QGroupBox('CPU 使用率')
        cpu_layout = QHBoxLayout()
        self.cpu_bar = QProgressBar()
        self.cpu_bar.setRange(0, 100)          # 百分比范围 0~100
        self.cpu_bar.setValue(0)
        self.cpu_label = QLabel('0.0 %')
        self.cpu_label.setMinimumWidth(80)
        cpu_layout.addWidget(self.cpu_bar)
        cpu_layout.addWidget(self.cpu_label)
        cpu_group.setLayout(cpu_layout)
        self.root_layout.addWidget(cpu_group)

        # ---------------- 3. 内存使用率 ----------------
        mem_group = QGroupBox('内存使用率')
        mem_layout = QVBoxLayout()
        mem_bar_layout = QHBoxLayout()
        self.memory_bar = QProgressBar()
        self.memory_bar.setRange(0, 100)
        self.memory_bar.setValue(0)
        self.memory_label = QLabel('0.0 %')
        self.memory_label.setMinimumWidth(80)
        mem_bar_layout.addWidget(self.memory_bar)
        mem_bar_layout.addWidget(self.memory_label)
        # 第二行显示“已用 / 总量”
        self.memory_detail_label = QLabel('0 B / 0 B')
        mem_layout.addLayout(mem_bar_layout)
        mem_layout.addWidget(self.memory_detail_label)
        mem_group.setLayout(mem_layout)
        self.root_layout.addWidget(mem_group)

        # ---------------- 4. 网卡收发数据 ----------------
        net_group = QGroupBox('网卡收发数据（所有网卡总和）')
        net_layout = QFormLayout()
        self.net_sent_label = QLabel('0 B')
        self.net_recv_label = QLabel('0 B')
        self.net_sent_rate_label = QLabel('0 B/s')
        self.net_recv_rate_label = QLabel('0 B/s')
        net_layout.addRow('累计发送：', self.net_sent_label)
        net_layout.addRow('累计接收：', self.net_recv_label)
        net_layout.addRow('发送速率：', self.net_sent_rate_label)
        net_layout.addRow('接收速率：', self.net_recv_rate_label)
        net_group.setLayout(net_layout)
        self.root_layout.addWidget(net_group)

        # ---------------- 5. 底部状态提示 ----------------
        self.status_label = QLabel('订阅状态：正在等待 /sys_status 数据...')
        self.root_layout.addWidget(self.status_label)

        self.setLayout(self.root_layout)

    def update_status(self, msg):
        """根据收到的消息刷新所有控件。"""

        # --- 采集时间：header.stamp 由秒(sec)和纳秒(nanosec)两部分组成 ---
        sec = msg.header.stamp.sec
        millisec = msg.header.stamp.nanosec // 1_000_000  # 纳秒 -> 毫秒
        time_str = datetime.fromtimestamp(sec).strftime('%Y-%m-%d %H:%M:%S')
        self.time_label.setText('{}.{:03d}'.format(time_str, millisec))

        # --- CPU ---
        cpu = msg.cpu_percent
        self.cpu_bar.setValue(int(cpu))
        self.cpu_bar.setFormat('%.1f%%' % cpu)  # 进度条上显示一位小数
        self.cpu_label.setText('{:.1f} %'.format(cpu))

        # --- 内存 ---
        mem_percent = msg.memory_percent
        self.memory_bar.setValue(int(mem_percent))
        self.memory_bar.setFormat('%.1f%%' % mem_percent)
        self.memory_label.setText('{:.1f} %'.format(mem_percent))
        self.memory_detail_label.setText(
            '{} / {}'.format(
                human_bytes(msg.memory_used),
                human_bytes(msg.memory_total),
            )
        )

        # --- 网卡 ---
        self.net_sent_label.setText(human_bytes(msg.net_sent))
        self.net_recv_label.setText(human_bytes(msg.net_recv))
        self.net_sent_rate_label.setText(human_rate(msg.net_sent_rate))
        self.net_recv_rate_label.setText(human_rate(msg.net_recv_rate))

        # --- 底部状态 ---
        self.status_label.setText('订阅状态：数据刷新中（话题 /sys_status）')


def main(args=None):
    """节点 + 窗口的统一入口。"""
    # 1. 初始化 ROS2
    rclpy.init(args=args)

    # 2. 创建 Qt 应用（每个 Qt 程序有且只有一个 QApplication）
    app = QApplication(sys.argv)

    # 3. 创建订阅节点与主窗口，并把窗口注入节点
    node = SysStatusSub()
    window = SystemStatusWindow()
    node.window = window
    window.show()  # 显示窗口

    # 4. 用 QTimer 周期性驱动 ROS2 处理消息
    spin_timer = QTimer()
    # timeout_sec=0.0 表示非阻塞：有消息就处理，没有立即返回，
    # 不会卡住 Qt 界面
    spin_timer.timeout.connect(
        lambda: rclpy.spin_once(node, timeout_sec=0.0))
    spin_timer.start(100)  # 每 100ms 处理一次

    # 5. 进入 Qt 事件循环，关闭窗口后返回退出码
    exit_code = app.exec_()

    # 6. 清理资源
    spin_timer.stop()
    node.destroy_node()
    rclpy.shutdown()
    sys.exit(exit_code)


if __name__ == '__main__':
    main()
