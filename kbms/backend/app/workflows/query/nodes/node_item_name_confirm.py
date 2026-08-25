from app.domain.ports.doc_store import DocumentStore
from app.domain.ports.llm import LLMPort
from app.domain.ports.vector_db import ItemNameVectorDB
from app.workflows.query.base import NodeBase
from app.workflows.query.exceptions import StateFieldError
from app.workflows.query.state import QueryGraphState


class NodeItemNameConfirm(NodeBase):

    name: str = "node_item_name_confirm"
    
    def __init__(self,
                 mongo: DocumentStore, 
                 llm_service: LLMPort,
                 item_name_vector_db: ItemNameVectorDB):
        super().__init__()
        self._mongo = mongo
        self._llm_service = llm_service
        self._item_name_vector_db = item_name_vector_db

    def _validate_input_state(self, state: QueryGraphState) -> tuple[str, str]:
        session_id = state.get("session_id") 
        if not session_id:
            raise StateFieldError(field_name="session_id", message="State field 'session_id' missing")

        original_query = state.get("original_query")
        if not original_query:
            raise StateFieldError(field_name="original_query", message="State field 'original_query' missing")

        return session_id, original_query
    
    def _align_item_names(self, query_results) -> dict:
        """
        6 根据Milvus搜索评分，逐个对齐step4提取的item_names，生成「确认商品名」和「候选商品名」
        对齐规则（优先级a>b>c>d）：
            a  如果只有一个匹配结果评分高于0.85 → 直接确认该商品名
            b  如果多条匹配结果评分超过0.85 → 优先取与原始提取名相同的，无则取分数最高的
            c  如果无0.85分以上结果 → 取分数≥0.6的最高前5个作为候选
            d  如果无0.6分及以上结果 → 不返回任何商品名（确认+候选均为空）
        :param query_results: 列表[字典] - step5的返回结果，每个商品名的搜索匹配数据（格式同step5返回值）
        :return: 字典 - 商品名对齐结果，包含确认列表和候选列表，格式：
            {
                "confirmed_item_names": ["确认商品名1", "确认商品名2"],  # 去重后的确认商品名，无则空列表
                "options": ["候选商品名1", "候选商品名2", ...]          # 去重后的候选商品名，无则空列表
            }
        """
        # 1、初始化确认商品名列表（符合高置信度规则的商品名）
        confirmed_item_names: list[str] = []
        # 2、初始化候选商品名列表（低置信度，需用户确认的商品名）
        options: list[str] = []

        for res in query_results:
            # 提取原始的数据，商品名和匹配结果
            resolved_name = (res.get("resolved_name", "") or  "").strip()
            # 获取匹配的商品名，无就获取空列表
            matches = res.get("matches", []) or []
            # 若无匹配结果，直接跳过当前商品名的对齐
            if not matches:
                continue

            # 筛选高置信度匹配结果：评分>0.85
            high = [m for m in matches if m.get("score", 0) > 0.85]
            # 筛选中置信度匹配结果：评分≥0.6（仅高置信度为空时生效）
            mid = [m for m in matches if m.get("score", 0) >= 0.6]

            # 优化 ab 所有评分高于0.85的都可以直接确认
            if len(high) > 0:
                self.logger.info(f"LLM商品识别“{resolved_name}”检索到 {len(high)} 个高置信度的结果，{high}")
                for m in high:
                    confirmed_item_names.append(m.get("item_name"))
                continue
            # 筛选高置信度得分的结果： >= 0.65
            # # a  如果只有一个匹配结果评分高于0.85 → 直接确认该商品名
            # if len(high) == 1:
            #     confirmed_item_names.append(high[0].get("item_name"))
            #     continue
            #
            # # b  如果多条匹配结果评分超过0.85 → 优先取与原始提取名相同的，无则取分数最高的
            # if len(high) > 1:
            #     picked = None
            #     if extracted_name:
            #
            #         # 优先取与原始提取名相同的
            #         for m in high:
            #             if m.get("item_name") == extracted_name:
            #                 picked = m
            #                 break
            #
            #     if not picked:
            #         # 无则取分数最高的
            #         picked = high[0]
            #
            #     confirmed_item_names.append(picked.get("item_name"))
            #     continue

            # 规则c: 无0.85分以上结果，取≥0.6分的最高前3个作为候选
            # 注：高置信度列表high为空时才会走到此处（规则a/b均不满足）
            if len(mid) > 0:
                self.logger.info(f"LLM商品识别“{resolved_name}”检索到 {len(mid)} 个中置信度的结果，{mid}")
                # 取中置信度结果的前5个，加入候选列表
                for m in mid[:3]:
                    options.append(m.get("item_name"))

            # 规则d: 无0.6分及以上结果 → 不做任何操作，确认+候选列表均为空
        # 返回最终对齐结果：确认列表和候选列表均做去重处理（list(set())）
        return list(set(confirmed_item_names)), list(set(options))  # 去重，避免重复候选
    
    def _resolve_confirmation_branches(self, confirmed, options, history):
        """
        7 检查step6对齐后的商品名状态，分3种分支更新state，并同步更新历史消息的商品名关联
        :param state: 字典 - 原始会话状态，包含session_id/original_query等核心字段
        :param align_result: 字典 - step6的对齐结果
        :param history: 列表[字典] - 近期会话历史
        :return: 字典 - 更新后的会话状态，包含item_names/answer
        """
        # 分支A：有确认的商品名（高置信度，无需用户确认）
        if confirmed:
            # 收集历史消息中未关联商品名的消息ID（需批量更新关联）
            ids_to_update = []
            for msg in history:
                if not msg.get("item_names"):  # 仅更新item_names为空的历史消息
                    mid = msg.get("_id")  # 提取消息唯一ID
                    if mid:
                        ids_to_update.append(str(mid))  # 转为字符串，避免ID格式问题

            # 若存在需更新的消息ID，批量更新历史消息的商品名关联
            if ids_to_update:
                self._mongo.update_message_item_names(ids_to_update, confirmed)

            # 更新会话状态：设置确认商品名、改写后的查询
            # 返回更新后的状态
            return confirmed, ""

        # 分支B：无确认商品名，但有候选商品名（中置信度，需用户明确）
        if options:
            # 候选商品名拼接为字符串，格式："商品1、商品2、商品3"
            options_str = "、".join(options)
            # 构造向用户确认的提示语
            answer = f"您是想问以下哪个产品：{options_str}？请明确一下型号。"
            # 更新会话状态：设置确认提示语、清空商品名列表
            return [], answer

        # 分支C：无确认商品名，且无候选商品名（无匹配结果，需用户重新提供）
        return [], "抱歉，未找到相关产品，请提供准确型号以便我为您查询。"
    
    def _update_chat_history(self, session_id, message_id, original_query, rewritten_query, item_names, answer):
        # answer generated (provide options to confirm/reject), insert into chat history
        # if answer:
        #     self._mongo.save_chat_message(
        #         session_id=session_id,
        #         role="assistant",
        #         text=answer,
        #         rewritten_query="",
        #         item_names=item_names
        #     )
        # ASSISTANT ANSWER WILL BE SAVED AT THE LAST STEP< NOT HERE!

        # no answer generated yet, update user message with item names and rewritten query
        self._mongo.save_chat_message(
            session_id=session_id,
            role="user",
            text=original_query,
            rewritten_query=rewritten_query,
            item_names=item_names,
            message_id=message_id
        )
    
    def process(self, state: QueryGraphState) -> QueryGraphState:

        session_id, original_query = self._validate_input_state(state)

        history = self._mongo.get_recent_messages(session_id)

        message_id = self._mongo.save_chat_message(session_id, "user", original_query)

        guessed_item_names, rewritten_query = self._llm_service.resolve_item_name_and_rewrite_query(original_query, history)

        confirmed_item_names = []
        options = []
        if len(guessed_item_names) > 0:
            search_results = self._item_name_vector_db.hybrid_search_item_name(guessed_item_names)
            confirmed_item_names, options = self._align_item_names(search_results)
        else:
            self.logger.info("No item names resolved, skipping vector search...")

        confirmed_item_names, answer = self._resolve_confirmation_branches(confirmed_item_names, options, history)

        self._update_chat_history(session_id, message_id, original_query, rewritten_query, confirmed_item_names, answer)

        return {
            "history": history,
            "rewritten_query": rewritten_query,
            "item_names": confirmed_item_names,
            "answer": answer
        }