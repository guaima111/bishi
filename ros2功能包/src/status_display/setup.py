# -*- coding: utf-8 -*-
# setup.py —— status_display 的安装配置（ament_python 包标准写法）
from setuptools import setup

package_name = 'status_display'

setup(
    name=package_name,
    version='0.0.0',
    # 需要安装的 Python 包（与本目录同名的子文件夹）
    packages=[package_name],
    data_files=[
        # 注册到 ament 资源索引，让 ros2 pkg list 能找到本包
        ('share/ament_index/resource_index/packages',
         ['resource/' + package_name]),
        # 把 package.xml 安装到 share 目录
        ('share/' + package_name, ['package.xml']),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='student',
    maintainer_email='student@example.com',
    description='使用 psutil 采集系统状态，并通过 PySide2 窗口实时显示',
    license='Apache-2.0',
    tests_require=['pytest'],
    # 注册可执行命令：ros2 run status_display <名字>
    entry_points={
        'console_scripts': [
            'sys_status_pub = status_display.sys_status_pub:main',
            'sys_status_sub = status_display.sys_status_sub:main',
        ],
    },
)
