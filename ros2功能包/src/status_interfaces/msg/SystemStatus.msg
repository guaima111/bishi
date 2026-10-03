# SystemStatus.msg
# 系统状态消息：由 status_display 发布节点每秒采集一次并发布

# 标准消息头，header.stamp 表示本次数据的采集时间
std_msgs/Header header

float64 cpu_percent      # CPU 使用率（百分比，范围 0~100）
float64 memory_percent   # 内存使用率（百分比，范围 0~100）
float64 memory_total     # 内存总容量（单位：字节）
float64 memory_used      # 已使用内存（单位：字节）
float64 net_sent         # 网卡累计发送数据量（单位：字节，开机以来所有网卡总和）
float64 net_recv         # 网卡累计接收数据量（单位：字节，开机以来所有网卡总和）
float64 net_sent_rate    # 网卡发送速率（单位：字节/秒）
float64 net_recv_rate    # 网卡接收速率（单位：字节/秒）
