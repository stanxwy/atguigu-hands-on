from collections import defaultdict

from app.utils.sse_utils import SSEEvent, push_sse_event

# init with [] if key not exist
_tasks_running_list: dict[str, list[str]] = defaultdict(list)
_tasks_done_list: dict[str, list[str]] = defaultdict(list)

# init with {} if key not exist
_tasks_result: dict[str, dict[str, str]] = defaultdict(dict)

_tasks_status: dict[str, str] = {}

TASK_STATUS_PENDING = "pending"
TASK_STATUS_PROCESSING = "processing"
TASK_STATUS_COMPLETED = "completed"
TASK_STATUS_FAILED = "failed"

_NODE_NAME_TO_CN: dict[str, str] = {
    "upload_file": "上传文件",
    "node_entry": "检查文件",
    "node_pdf_to_md": "PDF转Markdown",
    "node_md_img": "Markdown图片处理",
    "node_document_split": "文档切分",
    "node_item_name_recognition": "主体名称识别",
    "node_bge_embedding": "向量生成",
    "node_import_milvus": "导入向量数据库",
    # "knowledge_graph_node": "导入知识图谱",
    "__end__": "处理完成",

    "node_item_name_confirm": "确认问题产品",
    "node_web_search_mcp": "网络搜索",
    "node_search_embedding": "切片搜索",
    "node_search_embedding_hyde": "切片搜索(假设性文档)",
    "node_rerank": "重排序",
    "node_rrf": "倒排融合",
    "node_answer_output": "生成答案",
    # "kg_search_node": "查询知识图谱"
}


def _to_cn(node_name: str) -> str:
    return _NODE_NAME_TO_CN.get(node_name, node_name)


def add_running_task(task_id: str, node_name: str) -> None:
    # if task_id not in _tasks_running_list, running list will be initialized to [] and returned
    running = _tasks_running_list[task_id]
    if node_name not in running:
        running.append(node_name)

def add_done_task(task_id: str, node_name: str) -> None:
    # remove existing node from running list then add to done list
    if node_name in _tasks_running_list[task_id]:
        _tasks_running_list[task_id].remove(node_name)

    done = _tasks_done_list[task_id]
    if node_name not in done:
        done.append(node_name)


def get_running_task_list(task_id: str) -> list[str]:
    return [_to_cn(n) for n in _tasks_running_list.get(task_id, [])]

def get_done_task_list(task_id: str) -> list[str]:
    return [_to_cn(n) for n in _tasks_done_list.get(task_id, [])]


def get_task_status(task_id: str) -> str:
    return _tasks_status.get(task_id, TASK_STATUS_PENDING)

def update_task_status(task_id: str, status_name: str, is_stream: bool = False) -> None:
    _tasks_status[task_id] = status_name
    # if is_stream:
    #     push_sse_event(
    #         task_id, 
    #         SSEEvent.PROGRESS, 
    #         {
    #             "status": get_task_status(task_id),
    #             "running_list": get_running_task_list(task_id),
    #             "done_list": get_done_task_list(task_id),
    #         }
    #     )

def set_task_result(task_id: str, key: str, value: str) -> None:
    _tasks_result[task_id][key] = value

def get_task_result(task_id: str, key: str, default: str = "") -> str:
    return _tasks_result.get(task_id, {}).get(key, default)


def clear_task(task_id: str):
    _tasks_running_list.pop(task_id, None)
    _tasks_done_list.pop(task_id, None)
    _tasks_status.pop(task_id, None)
    _tasks_result.pop(task_id, None)