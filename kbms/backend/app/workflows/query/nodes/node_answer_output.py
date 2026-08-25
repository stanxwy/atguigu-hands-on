import re

from app.domain.ports.doc_store import DocumentStore
from app.domain.ports.llm import LLMPort
from app.utils.sse_utils import SSEEvent, push_sse_event
from app.utils.task_utils import set_task_result
from app.workflows.query.base import NodeBase
from app.workflows.query.exceptions import StateFieldError
from app.workflows.query.prompt import ANSWER_PROMPT
from app.workflows.query.state import QueryGraphState

_MAX_CONTEXT_LENGTH = 12000
_EMPTY_CONTEXT = "无参考内容"
_NO_CHAT_HISTORY = "暂无历史对话"
_NO_ITEM_NAME = "无指定商品"
_ERROR_RESPONSE = "抱歉，生成回答时出现错误。"
_IMG_EXTENSIONS = ('.png', '.jpg', '.jpeg', '.gif', '.webp', '.bmp', '.svg')
_REGEX_MD_IMG = re.compile(r'!\[.*?\]\((.*?)\)')

class NodeAnswerOutput(NodeBase):

    name: str = "node_answer_output"

    def __init__(self, mongo: DocumentStore,
                 llm_service: LLMPort):
        super().__init__()
        self._mongo = mongo
        self._llm_service = llm_service

    def _validate_input_state(self, state: QueryGraphState):
        if "session_id" not in state:
            raise StateFieldError(field_name="session_id", message="State field 'session_id' missing", expected_type=str)
        if "original_query" not in state:
            raise StateFieldError(field_name="original_query", message="State field 'original_query' missing", expected_type=str)

    def _construct_prompt(self, reranked_docs: list[dict], history: list[dict], item_names: list[str], original_query: str, rewritten_query: str) -> str:
        available_chars = _MAX_CONTEXT_LENGTH

        context_str, available_chars = self._format_reranked_docs(reranked_docs or [], available_chars)

        history_str = self._format_chat_history(history or [], available_chars)

        item_names_str = ", ".join(item_names) if item_names else _NO_ITEM_NAME

        question = rewritten_query or original_query

        prompt = ANSWER_PROMPT.format(
            context=context_str or _EMPTY_CONTEXT,
            history=history_str if history_str else _NO_CHAT_HISTORY,
            item_names=item_names_str,
            question=question,
        )
        self.logger.info(f"Prompt constructed: \n{prompt}")
        return prompt

    def _format_reranked_docs(self, reranked_docs: list[dict], available_chars: int) -> tuple[str, int]:
        formatted_lines = []
        used_chars = 0
        for idx, doc in enumerate(reranked_docs, start=1):
            
            meta_tags = [f"[{idx}]"]

            for field, template in [
                ("source", "[source={}]"),
                ("chunk_id", "[chunk_id={}]"),
                ("url", "[url={}]"),
                ("title", "[title={}]"),
            ]:
                field_value = str(doc.get(field)).strip()
                if field_value:
                    meta_tags.append(template.format(field_value))

            relevance_score = doc.get("score")
            if relevance_score is not None:
                meta_tags.append(f"[score={float(relevance_score):.4f}]")

            doc_entry = " ".join(meta_tags) + "\n" + doc.get("content")

            if used_chars + len(doc_entry) > available_chars:
                break

            formatted_lines.append(doc_entry)
            used_chars += len(doc_entry) + 2

        return "\n\n".join(formatted_lines), available_chars - used_chars

    def _format_chat_history(self, chat_history: list[dict], available_chars: int) -> str:
        formatted_lines = []
        used_chars = 0
        for message in chat_history:
            role = message.get("role", "")
            text = message.get("text", "")
            if not text or not role:
                continue
            formatted_line = f"{role}: {text}"
            used_chars += len(formatted_line) + 1

            if used_chars > available_chars:
                return "\n".join(formatted_lines)

            formatted_lines.append(formatted_line)

        return "\n".join(formatted_lines)

    def _generate_response(self, session_id: str, is_stream: bool, prompt: str) -> str:
        self.logger.info("---Step 3: LLM Generation---")
        llm = self._llm_service.get_llm_client()
        if is_stream:
            self.logger.info(f"Streaming mode, session: {session_id}")
            final_text = ""
            try:
                for chunk in llm.stream(prompt):
                    delta = getattr(chunk, "content", "") or ""
                    if delta:
                        final_text += delta
                        push_sse_event(session_id, SSEEvent.DELTA, {"delta": delta})
                self.logger.info(f"Streaming completed, content length: {len(final_text)}")
            except Exception as e:
                self.logger.exception(f"Error streaming LLM: {e!s}", stack_info=True)
                push_sse_event(session_id, SSEEvent.ERROR, {"error": str(e)})
            return final_text
        else:
            self.logger.info(f"Blocking mode, session: {session_id}")
            try:
                response = llm.invoke(prompt)
                content = response.content
                set_task_result(session_id, "answer", content)
                self.logger.info(f"Generation completed, content length: {len(content)}")
                return content
            except Exception as e:
                self.logger.exception(f"Error invoking LLM: {e!s}", stack_info=True)
                return _ERROR_RESPONSE

    def _extract_images_from_docs(self, docs):
        images = []
        seen = set() # use set to avoid duplicate
        if not docs:
            return []
        self.logger.info(f"Starting to extract images, docs to be processed: {len(docs)}")

        for i, doc in enumerate(docs or []):
            # check url field in rerank docs (web search results)
            url = (doc.get("url") or "").strip()
            if url and url.lower().endswith(_IMG_EXTENSIONS) and url not in seen:
                self.logger.debug(f"Image url found in doc[{i}] field: {url}")
                seen.add(url)
                images.append(url)

            # check content field in rerank docs (vector db chunks)
            text = (doc.get("content") or "").strip()
            if text:
                matches = _REGEX_MD_IMG.findall(text)
                for img_url in matches:
                    img_url = img_url.strip()
                    if img_url and img_url not in seen:
                        self.logger.debug(f"Image url found in doc{{i}} content: {img_url}")
                        seen.add(img_url)
                        images.append(img_url)
        self.logger.info(f"Unique images extracted: {len(images)} \n{images}")
        return images
    
    def _write_history(self, session_id: str, item_names: list[str], answer: str, image_urls = None) -> QueryGraphState:
        try:
            if answer:
                self._mongo.save_chat_message(
                    session_id=session_id,
                    role="assistant",
                    text=answer,
                    rewritten_query="",
                    item_names=item_names,
                    image_urls=image_urls,
                    message_id=None
                )
        except Exception as e:
            self.logger.exception(f"Error saving chat message: {e!s}", stack_info=True)
    
    def process(self, state: QueryGraphState) -> QueryGraphState:
        self._validate_input_state(state)
        task_id = state.get("task_id")
        session_id = state.get("session_id")
        original_query = state.get("original_query")
        rewritten_query = state.get("rewritten_query")
        item_names = state.get("item_names")
        history = state.get("history")
        reranked_docs = state.get("reranked_docs")
        answer = state.get("answer")
        is_stream = state.get("is_stream")
        image_urls = []

        if answer:
            if is_stream:
                push_sse_event(session_id, SSEEvent.DELTA, {"delta": answer})
            else:
                set_task_result(task_id, "answer", answer)
        else:
            prompt = self._construct_prompt(reranked_docs, history, item_names, original_query, rewritten_query)

            generated_answer = self._generate_response(session_id, is_stream, prompt)
            self.logger.debug(f"Generated answer: \n{generated_answer}")

            image_urls = self._extract_images_from_docs(reranked_docs)

        final_answer = answer or generated_answer
        self._write_history(session_id, item_names, final_answer, image_urls)

        self.logger.info(f"Push final event: {image_urls}")
        if is_stream:
            push_sse_event(session_id, SSEEvent.FINAL,
                {
                    "answer": final_answer,
                    "status": "completed",
                    "image_urls": image_urls
                })
        return {
            "answer": final_answer
        }