import base64
import json
import logging
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

from app.domain.ports.llm import LLMPort
from app.infra.config.settings import Settings
from app.workflows.ingestion.prompt import (
    IMAGE_CAPTION_PROMPT,
    ITEM_NAME_SYSTEM_PROMPT,
    ITEM_NAME_USER_PROMPT_TEMPLATE,
)
from app.workflows.query.prompt import (
    HYDE_PROMPT,
    ITEM_NAME_EXTRACT_SYSTEM_PROMPT,
    ITEM_NAME_EXTRACT_TEMPLATE,
)

logger = logging.getLogger(__name__)

_DEFAULT_IMAGE_CAPTION = "alt text"

class DashScopeService(LLMPort):
    def __init__(self, settings: Settings):
        self._settings = settings
        self._llm_client_cache = {}

    def get_llm_client(self, model: str | None = None, json_mode: bool = False) -> ChatOpenAI:
        logger.debug(f"Getting LangChain ChatOpenAI {model} client instance...")
        m = model or self._settings.llm_default_model

        key = (m, json_mode)
        if key in self._llm_client_cache:
            return self._llm_client_cache[key]

        extra_body = {"enable_thinking": False}

        model_kwargs: dict = {}
        if json_mode:
            model_kwargs["response_format"] = {"type": "json_object"}

        llm: ChatOpenAI = ChatOpenAI(
            model=m,
            api_key=self._settings.openai_api_key,
            base_url=self._settings.openai_api_base,
            temperature=self._settings.llm_temperature,
            extra_body=extra_body,
            model_kwargs=model_kwargs
        )
        self._llm_client_cache[key] = llm
        logger.info(f"LangChain ChatOpenAI {key} client instance created...")
        return llm

    def generate_image_caption(self, image_path: str, doc_stem: str, image_context: tuple[str, str]) -> str:
        with open(image_path, "rb") as img_file:
            base64_image = base64.b64encode(img_file.read()).decode("utf-8")
        try:
            chat_model = self.get_llm_client(self._settings.vl_model)
            user_prompt = IMAGE_CAPTION_PROMPT.format(
                doc_stem=doc_stem,
                pre_context=image_context[0],
                post_context=image_context[1]
            )
            messages = [{
                "role": "user",
                "content": [{
                    "type": "text",
                    "text": user_prompt
                }, {
                    "type": "image_url",
                    "image_url": { "url": f"data:image/jpeg;base64,{base64_image}" }
                }]
            }]
            logger.debug(f"Requesting VLM to generate image caption {image_path}")
            response = chat_model.invoke(messages)
            logger.info(f"Image caption generated: {response.content}")
            # logger.verbose(json.dumps(response, ensure_ascii=False, indent=2)) # Object of type AIMessage is not JSON serializable
            return response.content.strip().replace("\n", "")
        except Exception as e:
            logger.exception(f"Error generating image caption for {image_path}: {e!s}", stack_info=True)
            return _DEFAULT_IMAGE_CAPTION
    
    def identify_main_product(self, filename: str, context: str) -> str:
        if not context:
            return filename
        try:
            llm = self.get_llm_client()
            user_prompt = ITEM_NAME_USER_PROMPT_TEMPLATE.format(
                filename=filename, context=context
            )
            messages = [
                SystemMessage(content=ITEM_NAME_SYSTEM_PROMPT),
                HumanMessage(content=user_prompt)
            ]
            response = llm.invoke(messages)
            product_name = response.content
            logger.info(f"Item name identified: {product_name}")
            # data cleanup
            product_name = (product_name.replace(" ", "")
                            .replace("\n", "")
                            .replace("\t", "")
                            .replace("\r", ""))
            if not product_name:
                return filename
            return product_name
        except Exception as e:
            logger.exception(f"Error identifying item name for {filename}: {e!s}", stack_info=True)
            return filename
    
    def resolve_item_name_and_rewrite_query(self, query: str, history: list[dict[str, Any]]) -> tuple[list[str], str]:
        try:
            history_text = ""
            for msg in history:
                role = msg.get("role")
                content = msg.get("text")
                history_text += f"{role}: {content}\n"

            user_prompt = ITEM_NAME_EXTRACT_TEMPLATE.format(
                history_text=history_text,
                query=query
            )
            logger.debug(f"User prompt for LLM: \n{user_prompt}")
            messages = [
                SystemMessage(content=ITEM_NAME_EXTRACT_SYSTEM_PROMPT),
                HumanMessage(content=user_prompt)
            ]
            chat_model = self.get_llm_client(model=self._settings.item_model, json_mode=True)
            response = chat_model.invoke(messages)
            content = response.content
            logger.info(f"LLM response: \n{response}")

            if content.startswith("```json"):
                content = content.replace("```json", "").replace("```", "")
            result = json.loads(content)
            item_names = result.get("item_names", [])
            item_names = [
                name.replace(" ", "").replace("\n", "").replace("\t", "").replace("\r", "")
                for name in item_names
            ]
            rewritten_query = result.get("rewritten_query", query)

            return item_names, rewritten_query
        except Exception as e:
            logger.exception(f"Error calling LLM: {e!s}", stack_info=True)
            return [], query

    def generate_hyde_doc(self, rewritten_query: str) -> str:
        try:
            llm = self.get_llm_client()
            hyde_prompt = HYDE_PROMPT.format(rewritten_query=rewritten_query)
            response = llm.invoke(hyde_prompt)
            logger.info(f"Hyde document generated: \n{response}")
            return response.content
        except Exception as e:
            logger.exception(f"Error generating Hyde document: {e!s}", stack_info=True)
            raise e