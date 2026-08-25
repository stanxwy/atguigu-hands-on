import re

from langchain_text_splitters import RecursiveCharacterTextSplitter

from app.workflows.ingestion.base import BaseNode
from app.workflows.ingestion.exceptions import StateFieldError
from app.workflows.ingestion.state import ImportGraphState

_REGEX_TITLE_LINE = r'^\s*#{1,6}\s+.+'
_REGEX_CODE_BLOCK_MARKER = r'^(`{3,}|~{3,})'
_NO_TITLE = "No Title"

class NodeDocumentSplit(BaseNode):

    name: str = "node_document_split"

    def _validate_input_state(self, state: ImportGraphState) -> tuple[str, str]:
        file_title = state.get("file_title")
        if not file_title:
            raise StateFieldError(field_name="file_title", message="filename is required", expected_type=str)

        md_content = state.get("md_content")
        if not md_content:
            raise StateFieldError(field_name="md_content", message="md_content cannot be empty", expected_type=str)

        md_content = md_content.replace("\r\n", "\n").replace("\r", "\n")
        return md_content, file_title

    def _split_by_headings(self, content: str, file_title: str) -> tuple[list[dict[str, str]], int, int]:
        sections = []
        def _flush_section():
            if not current_lines:
                return
            sections.append({
                "parent_title": _find_parent_title(current_title, sections),
                "title": current_title,
                "content": "\n".join(current_lines),
                "file_title": file_title,
            })
        
        def _find_parent_title(current_title: str, sections: list[dict[str, str]]) -> str:
            current_level = _get_title_level(current_title)
            if current_level is None or current_level <= 1:
                return ""
            
            for section in reversed(sections):
                parent_title = section.get("title", "")
                parent_level = _get_title_level(parent_title)
                
                if parent_level is not None and parent_level < current_level:
                    return parent_title
            return ""

        def _get_title_level(title: str) -> int | None:
            if not title:
                return None
            match = re.match(r'^(#{1,6})\s+', title)
            if not match:
                return None
            return len(match.group(1))
        
        current_title = ""
        current_lines = []
        title_count = 0
        in_code_block = False

        lines = content.split("\n")
        for line in lines:
            stripped_line = line.strip()

            code_block_marker_match = re.match(_REGEX_CODE_BLOCK_MARKER, stripped_line)
            if code_block_marker_match:
                marker = code_block_marker_match.group(1)
                if not in_code_block:
                    in_code_block = True
                    code_block_start_marker = marker
                elif in_code_block and stripped_line == code_block_start_marker:
                    in_code_block = False
                    code_block_start_marker = None
                current_lines.append(line)
                continue

            is_heading_line = (not in_code_block) and re.match(_REGEX_TITLE_LINE, line)
            if is_heading_line:
                _flush_section()
                current_title = stripped_line
                current_lines = [current_title]
                title_count += 1
                self.logger.info(f"Found heading line: {current_title}")
            else:
                current_lines.append(line)

        _flush_section()
        self.logger.info(f"Document split by headings completed, total {len(sections)} sections, title count: {title_count}, line count: {len(lines)}")
        return sections, title_count, len(lines)

    def _split_and_merge(self, sections: list[dict[str, str]]) -> list[dict[str, str]]:
        splitted = []
        for sec in sections:
            splitted.extend(self._split_overlong_chunk(sec))
        self.logger.info(f"Chunks after splitting: {len(splitted)}")

        merged = self._merge_tiny_chunks(splitted)
        self.logger.info(f"Chunks after merging: {len(merged)}")
        return merged

    def _split_overlong_chunk(self, section: dict[str, str]) -> list[dict[str, str]]:
        content = section.get("content", "")
        if len(content) <= self.config.max_content_length:
            return [section]

        title = section.get("title", "")
        prefix = f"{title}\n\n" if title else ""
        available_len = self.config.max_content_length - len(prefix)
        if available_len <= 0:
            self.logger.info(f"Long section title, cannot be further splitted: {title[:20]}...")
            return [section]

        # remove duplicate title
        body = content
        if title and body.lstrip().startswith(title):
            body = body[body.find(title) + len(title):].lstrip()

        splitter = RecursiveCharacterTextSplitter(
            chunk_size=available_len,
            chunk_overlap=0,
            separators=["\n\n", "\n", "。", "！", "？", "；", ".", "!", "?", ";", " "],
        )

        splitted = []
        chunks = splitter.split_text(body)
        for idx, chunk in enumerate(chunks, start=1):
            text = chunk.strip()
            if not text:
                continue
            full_text = (prefix + text).strip()
            splitted.append({
                "title": f"{title}-{idx}" if title else f"chunk-{idx}",
                "content": full_text,
                "parent_title": title,
                "part": idx,
                "file_title": section.get("file_title"),
            })
        self.logger.info(f"Overlong section ({title}) splitted into {len(splitted)} chunks")
        return splitted

    def _merge_tiny_chunks(self, chunks: list[dict[str, str]]) -> list[dict[str, str]]:
        if not chunks:
            self.logger.info("No sections to merge")
            return []

        merged = []
        to_merge = None 
        merge_count = 1
        for chunk in chunks:
            if to_merge is None:
                to_merge = chunk
                continue
            
            curr_len = len(to_merge["content"])
            is_current_short = curr_len < self.config.min_content_length
            is_same_parent = to_merge.get("parent_title") == chunk.get("parent_title")
            self.logger.debug(f'Checking merge condition: prev {to_merge.get("parent_title")}, current {chunk.get("parent_title")}')

            if is_current_short and is_same_parent:
                # remove duplicate parent title from next content before merge
                parent_title = chunk.get("parent_title", "")
                next_content = chunk["content"]
                self.logger.debug(f"Next length: {len(next_content)}")
                if parent_title and next_content.startswith(parent_title):
                    next_content = next_content[len(parent_title):].lstrip()
                # merge content, space-separated
                to_merge["content"] += "\n\n" + next_content
                merge_count += 1
                # update sub-chunk part
                if "part" in chunk:
                    to_merge["part"] = chunk["part"]
                self.logger.debug(f">>> Merged tiny chunk: {curr_len} + {len(next_content)} -> {len(to_merge['content'])}, {merge_count} chunks")
            else:
                # reset merge cursor if merge condition not satisfied
                self.logger.debug(f"<<< Merge condition not satisfied, current merged length: {curr_len}, same parent: {is_same_parent}")
                merged.append(to_merge)
                to_merge = chunk
                merge_count = 1

        # append the last chunk
        if to_merge is not None:
            merged.append(to_merge)

        self.logger.debug(f"Tiny chunks merged {len(chunks)} -> {len(merged)}")
        return merged

    def process(self, state: ImportGraphState) -> ImportGraphState:

        content, file_title = self._validate_input_state(state)

        sections, title_count, lines_count = self._split_by_headings(content, file_title)
        # no headings fallback
        if title_count == 0:
            self.logger.warning(f"No headings detected, process as a single section: {file_title}")
            sections = [{"title": _NO_TITLE, "content": content, "file_title": file_title}]

        chunks = self._split_and_merge(sections)

        self.logger.info("-" * 50 + " chunking stats " + "-" * 50)
        self.logger.info(f"MD file line count: {lines_count}")
        self.logger.info(f"Final chunks count: {len(chunks)}")
        self.backup_json(state, chunks, "chunks.json")
        return { "chunks": chunks }