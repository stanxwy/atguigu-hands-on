"""隔离环境服务：docker-py 容器生命周期 + 只读命令执行。

对齐《安全规范》§5：只读挂载、network=none、cap_drop=ALL、非 root、
read_only 根文件系统、资源限制。无 Docker 时允许本地回退（仅开发/演示，
由 ``ISOLATION_FALLBACK_LOCAL`` 控制）。
"""

import asyncio
import logging
import subprocess
from pathlib import Path
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.errors import IsolationError
from app.services import config_service
from app.utils.path_safety import validate_host_path

logger = logging.getLogger("app.isolation")

try:  # docker SDK 可选导入，缺失时降级为本地回退
    import docker
    from docker.errors import DockerException

    _DOCKER_IMPORTED = True
except ImportError:  # pragma: no cover
    docker = None  # type: ignore[assignment]
    DockerException = Exception
    _DOCKER_IMPORTED = False


class IsolationService:
    """隔离环境管理器（容器创建/启动/停止/销毁 + 命令执行）。"""

    CONTAINER_PREFIX = "cse-"

    def __init__(self) -> None:
        self._client: Any = None
        self._available = False
        self._containers: dict[int, Any] = {}
        self._source_dirs: dict[int, Path] = {}
        self._init_client()

    def _init_client(self) -> None:
        """探测 Docker 引擎可用性。"""
        if not _DOCKER_IMPORTED:
            logger.warning("docker SDK 未安装，隔离环境将使用本地回退模式")
            return
        try:
            self._client = docker.from_env()
            self._client.ping()
            self._available = True
        except DockerException as exc:
            logger.warning("Docker 不可用，隔离环境将使用本地回退模式: %s", exc)

    def is_available(self) -> bool:
        """返回 Docker 是否可用。"""
        return self._available

    def get_source_dir(self, project_id: int) -> Path | None:
        """返回项目已解析的源码目录（本地路径或克隆目录）。"""
        return self._source_dirs.get(project_id)

    async def resolve_source_dir(self, project: Any) -> Path:
        """解析项目源码目录。

        - ``local_path``：校验后返回规范化绝对路径；
        - ``git_repo``：浅克隆到 ``workspace/{id}/src``（仅 HTTPS 公开仓库）。

        Args:
            project: Project 模型实例。

        Returns:
            源码目录绝对路径。

        Raises:
            IsolationError: 仓库克隆失败。
        """
        if project.source_type == "git_repo":
            dest = settings.workspace_path / str(project.id) / "src"
            await self._clone_repo(project.source_path, dest)
            return dest
        return validate_host_path(project.source_path)

    async def _clone_repo(self, url: str, dest: Path) -> None:
        """浅克隆公开 HTTPS 仓库（参数数组，无 shell 拼接）。"""
        dest.parent.mkdir(parents=True, exist_ok=True)
        try:
            await asyncio.to_thread(
                subprocess.run,
                ["git", "clone", "--depth", "1", url, str(dest)],
                check=True,
                capture_output=True,
            )
        except (subprocess.CalledProcessError, FileNotFoundError) as exc:
            raise IsolationError(f"源码仓库克隆失败: {url}") from exc

    async def prepare_environment(
        self, db: AsyncSession, project: Any, source_dir: Path
    ) -> str | None:
        """准备隔离环境：记录源码目录并创建容器（或本地回退）。

        Args:
            db: 数据库会话（读取隔离配置）。
            project: Project 模型实例。
            source_dir: 已解析的源码目录。

        Returns:
            容器 ID（Docker 可用时）或 None（本地回退时）。
        """
        self._source_dirs[project.id] = source_dir
        # 显式开启本地回退时强制不走 Docker（开发/演示；生产应关闭本开关）
        if settings.isolation_fallback_local:
            logger.warning(
                "本地回退模式（ISOLATION_FALLBACK_LOCAL=true）：项目 %s 不创建隔离容器",
                project.id,
            )
            return None
        if not self._available:
            raise IsolationError(
                "Docker 不可用且已关闭本地回退（ISOLATION_FALLBACK_LOCAL=false）"
            )

        image = await config_service.get_value(
            db, "isolation.default_image", settings.isolation_default_image
        )
        network_mode = await config_service.get_value(
            db, "isolation.network_mode", settings.isolation_network_mode
        )
        mount_readonly = await config_service.get_value(
            db, "isolation.mount_readonly", True
        )
        container = await asyncio.to_thread(
            self._create_container,
            str(image),
            str(source_dir),
            str(network_mode),
            bool(mount_readonly),
            project.id,
        )
        self._containers[project.id] = container
        return container.id

    def _create_container(
        self,
        image: str,
        host_src: str,
        network_mode: str,
        mount_readonly: bool,
        project_id: int,
    ) -> Any:
        """创建隔离容器（安全基线 ISO-01~05）。"""
        mode = "ro" if mount_readonly else "rw"
        return self._client.containers.run(
            image=image,
            name=f"{self.CONTAINER_PREFIX}{project_id}",
            command=["sleep", "infinity"],
            network_mode=network_mode,
            volumes={host_src: {"bind": "/src", "mode": mode}},
            read_only=True,
            tmpfs={"/tmp": "size=64m"},
            cap_drop=["ALL"],
            security_opt=["no-new-privileges:true"],
            mem_limit="512m",
            cpu_quota=50000,
            pids_limit=256,
            user="1000:1000",
            detach=True,
        )

    async def stop_environment(self, project_id: int) -> None:
        """停止隔离容器（不删除）。"""
        container = self._containers.pop(project_id, None)
        self._source_dirs.pop(project_id, None)
        if container is not None:
            await asyncio.to_thread(self._safe_stop, container)

    async def destroy_environment(self, project_id: int) -> None:
        """销毁隔离容器（停止 + 删除），失败不阻塞（记录告警）。"""
        container = self._containers.pop(project_id, None)
        self._source_dirs.pop(project_id, None)
        if container is not None:
            await asyncio.to_thread(self._safe_destroy, container)

    async def exec_command(
        self, project_id: int, argv: list[str], timeout: int
    ) -> tuple[int, str]:
        """执行白名单命令（容器内或本地回退），返回 (退出码, 输出)。

        Args:
            project_id: 项目 ID。
            argv: 参数数组（已由 command_whitelist 构建）。
            timeout: 命令超时（秒）。
        """
        container = self._containers.get(project_id)
        if container is None:
            return await asyncio.to_thread(self._exec_local, argv, timeout)
        return await asyncio.to_thread(self._exec_docker, container, argv, timeout)

    @staticmethod
    def _exec_docker(container: Any, argv: list[str], timeout: int) -> tuple[int, str]:
        """容器内执行（docker exec 参数数组，禁 shell）。"""
        result = container.exec_run(argv, demux=False, stdout=True, stderr=True)
        exit_code = int(result.exit_code or 0)
        output = (result.output or b"").decode("utf-8", errors="replace")
        return exit_code, output

    @staticmethod
    def _exec_local(argv: list[str], timeout: int) -> tuple[int, str]:
        """本地回退执行（参数数组 + shell=False，无 shell 注入面）。

        仅当命令在宿主机 PATH 中存在时可用；否则返回非零退出码。
        """
        try:
            result = subprocess.run(
                argv,
                capture_output=True,
                timeout=timeout,
                shell=False,
                text=True,
            )
            return result.returncode, (result.stdout or "") + (result.stderr or "")
        except FileNotFoundError:
            return 127, f"命令不可用: {argv[0]}"
        except subprocess.TimeoutExpired:
            return 124, "命令超时"

    @staticmethod
    def _safe_stop(container: Any) -> None:
        try:
            container.stop(timeout=5)
        except Exception as exc:  # noqa: BLE001  容器已退出属正常
            logger.warning("停止容器失败: %s", exc)

    @staticmethod
    def _safe_destroy(container: Any) -> None:
        try:
            container.remove(force=True)
        except Exception as exc:  # noqa: BLE001  见 SPEC §2.4 文件/容器清理不阻塞
            logger.warning("销毁容器失败（不阻塞删除事务）: %s", exc)


isolation_service = IsolationService()
