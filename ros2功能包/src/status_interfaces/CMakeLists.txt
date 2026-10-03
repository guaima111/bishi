# CMakeLists.txt —— status_interfaces（自定义消息包）
cmake_minimum_required(VERSION 3.8)
project(status_interfaces)

# 编译器选项：开启常用警告，方便发现代码问题
if(CMAKE_COMPILER_IS_GNUCXX OR CMAKE_CXX_COMPILER_ID MATCHES "Clang")
  add_compile_options(-Wall -Wextra -Wpedantic)
endif()

# ament_cmake 是 ROS2 的 CMake 构建系统
find_package(ament_cmake REQUIRED)
# rosidl_default_generators 负责把 .msg 文件生成为 Python/C++ 可用的代码
find_package(rosidl_default_generators REQUIRED)
# Header 中使用了 std_msgs/Header -> builtin_interfaces/Time
find_package(std_msgs REQUIRED)
find_package(builtin_interfaces REQUIRED)

# 声明要生成的消息接口文件
rosidl_generate_interfaces(${PROJECT_NAME}
  "msg/SystemStatus.msg"
  DEPENDENCIES std_msgs builtin_interfaces
)

# 告诉 ament 本包是一个消息接口包
ament_package()
