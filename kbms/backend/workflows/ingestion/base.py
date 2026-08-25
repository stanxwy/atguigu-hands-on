import logging
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional, TypeVar

from app.utils.backup_utils import backup_json
from app.utils.task_utils import add_done_task, add_running_task
from app.workflows.ingestion.exceptions import ImportProcessError
from app.workflows.ingestion.import_config import ImportConfig, get_config
from app.workflows.ingestion.state import ImportGraphState

T = TypeVar("T", bound="ImportGraphState")

"""
1、抽象的类（ABC），子类需要实现这个类
2、抽象的方法（@abstractmethod process），子类需要实现这个方法
3、name属性，子类必须覆盖这个属性
4、__init__() 方法中初始化了日志记录器，日志记录器的名字是 self所在类的名字
5、__init__() 方法中初始化了全局配置，获取全局单例配置对象
6、__call__() 方法的调用时机  
    (1)对象 = 类名() 
    (2)结果 = 对象()     圆括号调用了__call__()方法
7、self.process()， 当前这句话是从哪调用过来的，process()就定义在哪个位置
8、未来可以在父类的process()中实现任务追踪
9、封装了统一日志处理，使用logging、colorlog
    注意：使用日志记录器记录日志时一定要先激活日志setup_logging(logging.INFO)，并指定日志级别
"""

class BaseNode(ABC):
    name: str = "base_node"

    def __init__(self, config: Optional[ImportConfig] = None):
        self.config = config or get_config()
        self.logger = logging.getLogger(f"import.{self.name}")

    def __call__(self, state: T) -> T:
        try:
            task_id = state.get("task_id")
            self.logger.info(f"--- {self.name} started ---")
            add_running_task(task_id, self.name)

            result = self.process(state)

            add_done_task(task_id, self.name)
            self.logger.info(f"--- {self.name} done ---")
            return result
        except Exception as e:
            self.logger.exception(f"Error running node {self.name}: {e!s}", stack_info=True)
            raise ImportProcessError(
                message=str(e),
                node_name=self.name,
                cause=e
            )

    @abstractmethod
    def _validate_input_state(self, state: T):
        ...

    @abstractmethod
    def process(self, state: T) -> T:
        ...

    def backup_json(self, state: T, json_data: dict | list, file_name: str):
        file_path = Path(state.get("output_file_dir")) / state.get("file_title") / file_name 
        backup_json(file_path, json_data)