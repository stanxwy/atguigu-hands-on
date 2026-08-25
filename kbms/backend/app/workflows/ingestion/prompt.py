IMAGE_CAPTION_PROMPT = """这是"{doc_stem}"文件中的一张图片，图片上文部分为"{pre_context}"，下文部分为"{post_context}"，请用中文简要总结这张图片的内容，用于 Markdown 图片标题。尽量不要超过20个字"""

# System Prompt
ITEM_NAME_SYSTEM_PROMPT = "你是一个专业的商品名称识别模型，请根据提供的信息，识别商品名称。名称最好不要超过20个字"

# User Prompt Template
ITEM_NAME_USER_PROMPT_TEMPLATE = """
请从以下信息中识别出商品名称与型号：
文件名：{filename}

正文切片（用于辅助识别）：
{context}

要求：
1. 返回内容为字符串形式，最好是带品牌、型号和名称的完整商品名称。比如：苏伯尓5000W大功率电磁炉；
2. 返回结果应该只包含商品名称，不要添加任何解释或其他内容；
3. 如果无法识别商品名称,请返回空字符串。
"""