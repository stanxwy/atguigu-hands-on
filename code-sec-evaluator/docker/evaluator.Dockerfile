# =============================================================================
# 隔离环境评估镜像（对齐《安全规范》§5：非 root + 只读命令集 + 无 shell/网络工具）
#
# 构建：docker build -f docker/evaluator.Dockerfile -t sec-evaluator:latest .
# 说明：镜像仅内置只读命令工具（grep/find/cat/head/tail/sed/ls/file/stat），
#       不含交互式 shell、网络工具（curl/wget/nc 等），容器运行参数由
#       isolation_service 进一步收紧（network=none、cap_drop=ALL、read_only 等）。
# =============================================================================
FROM debian:bookworm-slim

# 仅安装只读分析所需的最小命令集，不安装任何网络/编译工具
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        coreutils \
        findutils \
        grep \
        sed \
        file \
        procps \
    && rm -rf /var/lib/apt/lists/*

# 创建非 root 低权限用户（UID 1000，与 isolation_service 的 user 参数一致）
RUN useradd -r -u 1000 -m -s /usr/sbin/nologin evaluator

# 以非 root 运行；源码以只读卷挂载到 /src
USER 1000:1000
WORKDIR /src

# 常驻进程（isolation_service 创建容器时以 command=["sleep","infinity"] 覆盖亦可）
CMD ["sleep", "infinity"]
