# -*- coding: utf-8 -*-
"""
sys_status_pub.py —— 系统状态发布节点

功能：
    以 1Hz 的频率使用 psutil 采集本机的 CPU 使用率、内存使用率、
    网卡收发数据量与收发速率，封装成自定义消息
    status_interfaces/msg/SystemStatus，发布到话题 /sys_status。

调试方法：
    ros2 topic list                 # 查看话题
    ros2 topic echo /sys_status     # 查看消息内容
    ros2 topic hz /sys_status       # 查看发布频率
"""
import time

import psutil  # 第三方库：跨平台系统信息采集（sudo apt install python3-psutil）
import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy, HistoryPolicy

# 从自定义消息包导入消息类型（colcon 编译 status_interfaces 后生成）
from status_interfaces.msg import SystemStatus


class SysStatusPub(Node):
    """系统状态发布者节点。"""

    def __init__(self):
        # 节点名：ros2 node list 中会显示 /sys_status_pub
        super().__init__('sys_status_pub')

        # ---- QoS 配置 ----
        # 系统状态属于“传感器式”数据：丢一两帧无所谓，只要最新一帧即可。
        # BEST_EFFORT：尽力传输（不保证可靠到达，延迟低）
        # KEEP_LAST + depth=1：订阅者端只缓存最新的 1 条消息
        qos_profile = QoSProfile(
            reliability=ReliabilityPolicy.BEST_EFFORT,
            history=HistoryPolicy.KEEP_LAST,
            depth=1,
        )

        # 创建发布者：消息类型、话题名、QoS
        self.publisher_ = self.create_publisher(
            SystemStatus, '/sys_status', qos_profile)

        # 创建周期定时器：每 1.0 秒触发一次回调（即发布频率 1Hz）
        self.timer_ = self.create_timer(1.0, self.timer_callback)

        # ---- psutil 初始化 ----
        # cpu_percent(interval=None) 第一次调用固定返回 0.0，
        # 它表示“距离上次调用到现在”的 CPU 平均使用率，
        # 因此先预热一次，之后在 1 秒定时器里调用就能得到真实值。
        psutil.cpu_percent(interval=None)

        # 记录上一次采样时的网卡计数与时间，用于计算收发速率。
        # net_io_counters() 返回开机以来【所有网卡总和】的累计字节数。
        counters = psutil.net_io_counters()
        self.last_net_sent_ = counters.bytes_sent
        self.last_net_recv_ = counters.bytes_recv
        # 使用单调时钟计算时间差，不受用户手动改系统时间影响
        self.last_time_ = time.monotonic()

        self.get_logger().info('系统状态发布节点已启动，发布话题：/sys_status')

    def timer_callback(self):
        """定时器回调：采集 -> 封装消息 -> 发布，每秒执行一次。"""

        # ---------- 1. 计算与上一帧的时间间隔（秒） ----------
        current_time = time.monotonic()
        # max(..., 1e-6) 防止除零
        dt = max(current_time - self.last_time_, 1e-6)
        self.last_time_ = current_time

        # ---------- 2. 采集 CPU 使用率（%） ----------
        cpu_percent = psutil.cpu_percent(interval=None)

        # ---------- 3. 采集内存信息 ----------
        # virtual_memory() 返回 namedtuple：
        #   total   总内存（字节）
        #   used    已用内存（字节）
        #   percent 使用率（%）
        memory = psutil.virtual_memory()

        # ---------- 4. 采集网卡收发数据量，并计算速率 ----------
        counters = psutil.net_io_counters()
        # 速率 = 本周期新增字节数 / 本周期时长
        net_sent_rate = (counters.bytes_sent - self.last_net_sent_) / dt
        net_recv_rate = (counters.bytes_recv - self.last_net_recv_) / dt
        # 更新基准值，供下一帧使用
        self.last_net_sent_ = counters.bytes_sent
        self.last_net_recv_ = counters.bytes_recv

        # ---------- 5. 组装消息 ----------
        msg = SystemStatus()
        # header.stamp 填入当前 ROS 时间（秒 + 纳秒）
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.header.frame_id = ''  # 本消息不涉及坐标系，留空即可

        msg.cpu_percent = float(cpu_percent)
        msg.memory_percent = float(memory.percent)
        msg.memory_total = float(memory.total)
        msg.memory_used = float(memory.used)
        msg.net_sent = float(counters.bytes_sent)
        msg.net_recv = float(counters.bytes_recv)
        msg.net_sent_rate = float(net_sent_rate)
        msg.net_recv_rate = float(net_recv_rate)

        # ---------- 6. 发布消息 ----------
        self.publisher_.publish(msg)

        # 在终端打印一行日志，方便观察节点是否正常工作
        self.get_logger().info(
            'CPU: {:5.1f}% | 内存: {:5.1f}% | '
            '发送: {:>8.1f} KB/s | 接收: {:>8.1f} KB/s'.format(
                cpu_percent,
                memory.percent,
                net_sent_rate / 1024.0,
                net_recv_rate / 1024.0,
            )
        )


def main(args=None):
    """节点入口函数（在 setup.py 的 entry_points 中注册）。"""
    # 初始化 ROS2 Python 客户端库
    rclpy.init(args=args)
    node = SysStatusPub()

    try:
        # 保持节点运行，不断处理定时器回调，Ctrl+C 时退出
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        # 资源清理
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
