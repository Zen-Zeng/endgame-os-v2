"""
文件处理器
用于解析不同格式的文件（PDF、Markdown、JSON 等）
"""
from typing import List, Dict, Any, Optional
from pathlib import Path
import json
import logging
from datetime import datetime
from pypdf import PdfReader

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class FileProcessor:
    """
    文件处理器类
    支持解析 PDF、Markdown、TXT、JSON 等格式
    """

    def __init__(self, chunk_size: int = 1000, chunk_overlap: int = 200):
        """
        初始化文件处理器

        Args:
            chunk_size: 文本切分大小
            chunk_overlap: 文本切分重叠大小
        """
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    def parse_file(self, file_path: str) -> List[str]:
        """
        根据文件类型解析文件

        Args:
            file_path: 文件路径

        Returns:
            List[str]: 解析后的文本片段列表
        """
        path = Path(file_path)
        
        if not path.exists():
            logger.error(f"文件不存在: {file_path}")
            return []

        file_extension = path.suffix.lower()

        try:
            if file_extension == '.pdf':
                return self._parse_pdf(file_path)
            elif file_extension in ['.md', '.markdown']:
                return self._parse_markdown(file_path)
            elif file_extension == '.txt':
                return self._parse_text(file_path)
            elif file_extension == '.json':
                return self._parse_json(file_path)
            else:
                logger.warning(f"不支持的文件类型: {file_extension}")
                return []
        except Exception as e:
            logger.error(f"解析文件失败 {file_path}: {e}")
            return []

    def _parse_pdf(self, file_path: str) -> List[str]:
        """
        解析 PDF 文件

        Args:
            file_path: PDF 文件路径

        Returns:
            List[str]: 解析后的文本片段列表
        """
        try:
            reader = PdfReader(file_path)
            text = ""
            
            for page in reader.pages:
                text += page.extract_text() + "\n"
            
            chunks = self._chunk_text(text)
            logger.info(f"成功解析 PDF: {file_path}, 生成 {len(chunks)} 个片段")
            return chunks
        except Exception as e:
            logger.error(f"解析 PDF 失败: {e}")
            return []

    def _parse_markdown(self, file_path: str) -> List[str]:
        """
        解析 Markdown 文件

        Args:
            file_path: Markdown 文件路径

        Returns:
            List[str]: 解析后的文本片段列表
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                text = f.read()
            
            chunks = self._chunk_text(text)
            logger.info(f"成功解析 Markdown: {file_path}, 生成 {len(chunks)} 个片段")
            return chunks
        except Exception as e:
            logger.error(f"解析 Markdown 失败: {e}")
            return []

    def _parse_text(self, file_path: str) -> List[str]:
        """
        解析纯文本文件

        Args:
            file_path: 文本文件路径

        Returns:
            List[str]: 解析后的文本片段列表
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                text = f.read()
            
            chunks = self._chunk_text(text)
            logger.info(f"成功解析文本文件: {file_path}, 生成 {len(chunks)} 个片段")
            return chunks
        except Exception as e:
            logger.error(f"解析文本文件失败: {e}")
            return []

    def _parse_json(self, file_path: str) -> List[str]:
        """
        解析 JSON 文件（支持 ChatGPT/Gemini 聊天记录导出）

        Args:
            file_path: JSON 文件路径

        Returns:
            List[str]: 解析后的文本片段列表
        """
        try:
            logger.info(f"开始解析 JSON 文件: {file_path}")
            
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            logger.info(f"成功加载 JSON 数据，开始提取文本")
            text = self._extract_text_from_json(data)
            logger.info(f"文本提取完成，共 {len(text)} 个字符")
            
            logger.info(f"开始文本分块")
            chunks = self._chunk_text(text)
            logger.info(f"成功解析 JSON: {file_path}, 生成 {len(chunks)} 个片段")
            return chunks
        except Exception as e:
            logger.error(f"解析 JSON 失败: {e}")
            return []

    def _extract_text_from_json(self, data: Any) -> str:
        """
        从 JSON 数据中提取文本（优化后的非递归实现）
        Args:
            data: JSON 数据
        Returns:
            str: 提取的文本
        """
        text_parts = []
        stack = [data]
        
        while stack:
            item = stack.pop()
            
            if isinstance(item, str):
                text_parts.append(item)
            elif isinstance(item, dict):
                # 先处理内容字段，再处理其他字段
                for key, value in item.items():
                    if key.lower() in ['content', 'message', 'text', 'value']:
                        if isinstance(value, str):
                            text_parts.append(value)
                        elif isinstance(value, (dict, list)):
                            stack.append(value)
                    elif isinstance(value, (dict, list)):
                        stack.append(value)
            elif isinstance(item, list):
                # 反转列表，保持原有顺序
                for sub_item in reversed(item):
                    stack.append(sub_item)
        
        return "\n".join(text_parts)

    def extract_conversations_with_time(self, file_path: str) -> List[Dict[str, Any]]:
        """
        从 JSON 文件中提取对话记录和时间信息

        Args:
            file_path: JSON 文件路径

        Returns:
            List[Dict[str, Any]]: 对话记录列表，包含时间信息
        """
        try:
            logger.info(f"开始提取对话记录和时间信息: {file_path}")
            
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            conversations = []
            
            # 处理 ChatGPT 导出格式（数组形式）
            if isinstance(data, list):
                for conv_data in data:
                    if 'mapping' in conv_data:
                        for conv_id, conv_item in conv_data['mapping'].items():
                            if 'message' in conv_item and conv_item['message']:
                                message = conv_item['message']
                                content = ""
                                
                                # 提取消息内容
                                if 'content' in message:
                                    message_content = message['content']
                                    
                                    # 处理 parts 数组格式
                                    if isinstance(message_content, dict) and 'parts' in message_content:
                                        parts = message_content['parts']
                                        if isinstance(parts, list):
                                            # 过滤掉空字符串
                                            content_parts = [str(part) for part in parts if part and str(part).strip()]
                                            content = " ".join(content_parts)
                                    # 处理直接字符串格式
                                    elif isinstance(message_content, str):
                                        content = message_content
                                    # 处理 text 字段
                                    elif 'text' in message_content:
                                        content = message_content['text']
                                
                                # 获取时间戳
                                create_time = message.get('create_time', '')
                                if create_time:
                                    # 转换为标准格式
                                    try:
                                        if isinstance(create_time, (int, float)):
                                            create_time = datetime.fromtimestamp(create_time).strftime('%Y-%m-%d %H:%M:%S')
                                        else:
                                            create_time = str(create_time)
                                    except:
                                        create_time = ""
                                
                                # 只添加非空内容
                                if content and content.strip():
                                    conversations.append({
                                        'id': conv_id,
                                        'content': content,
                                        'create_time': create_time
                                    })
            
            # 处理单对象格式（向后兼容）
            elif isinstance(data, dict):
                if 'mapping' in data:
                    for conv_id, conv_data in data['mapping'].items():
                        if 'message' in conv_data:
                            message = conv_data['message']
                            content = ""
                            
                            # 提取消息内容
                            if 'content' in message:
                                if isinstance(message['content'], list):
                                    content = " ".join([part.get('text', '') for part in message['content']])
                                else:
                                    content = message['content'].get('text', '')
                            
                            # 获取时间戳
                            create_time = message.get('create_time', '')
                            if create_time:
                                # 转换为标准格式
                                try:
                                    if isinstance(create_time, (int, float)):
                                        create_time = datetime.fromtimestamp(create_time).strftime('%Y-%m-%d %H:%M:%S')
                                    else:
                                        create_time = str(create_time)
                                except:
                                    create_time = ""
                            
                            conversations.append({
                                'id': conv_id,
                                'content': content,
                                'create_time': create_time
                            })
            
            # 处理其他格式
            elif 'conversations' in data:
                for conv in data['conversations']:
                    # 简化处理
                    conversations.append({
                        'id': conv.get('id', ''),
                        'content': conv.get('text', ''),
                        'create_time': conv.get('timestamp', '')
                    })
            
            logger.info(f"成功提取 {len(conversations)} 条对话记录")
            return conversations
        except Exception as e:
            logger.error(f"提取对话记录失败: {e}", exc_info=True)
            return []

    def _chunk_text(self, text: str) -> List[str]:
        """
        将文本切分成小块

        Args:
            text: 要切分的文本

        Returns:
            List[str]: 切分后的文本片段列表
        """
        if not text:
            logger.info("文本内容为空，无需分块")
            return []
        
        logger.info(f"开始分块，文本长度: {len(text)}, 块大小: {self.chunk_size}, 重叠大小: {self.chunk_overlap}")
        
        chunks = []
        start = 0
        total_length = len(text)
        processed = 0
        
        while start < total_length:
            end = start + self.chunk_size
            
            if end >= total_length:
                chunks.append(text[start:])
                break
            
            chunk = text[start:end]
            
            # 尝试在换行符或句号处断开
            last_newline = chunk.rfind('\n')
            last_period = chunk.rfind('.')
            
            # 只有当断开位置能让 start 至少前进 1 个字符时才使用
            # 公式：new_start = end - overlap, 要求 new_start > start => end > start + overlap
            min_end = start + self.chunk_overlap + 1
            best_break = max(last_newline, last_period)
            
            if best_break > 0:
                adjusted_end = start + best_break + 1
                # 确保调整后的 end 足够大，不会导致 start 倒退
                if adjusted_end > min_end:
                    end = adjusted_end
                    chunk = text[start:end]
            
            chunks.append(chunk)
            
            # 确保下一次开始位置严格大于当前开始位置
            next_start = end - self.chunk_overlap
            if next_start <= start:
                start = start + (self.chunk_size - self.chunk_overlap)
            else:
                start = next_start
            
            # 每处理10%的文本记录一次日志
            new_processed = int(start / total_length * 100)
            if new_processed >= processed + 10:
                logger.info(f"分块进度: {min(new_processed, 100)}%")
                processed = new_processed
        
        # 过滤掉空块
        filtered_chunks = [chunk.strip() for chunk in chunks if chunk.strip()]
        logger.info(f"分块完成，共生成 {len(filtered_chunks)} 个有效块")
        
        return filtered_chunks

    def get_file_metadata(self, file_path: str) -> Dict[str, Any]:
        """
        获取文件元数据

        Args:
            file_path: 文件路径

        Returns:
            Dict[str, Any]: 文件元数据
        """
        path = Path(file_path)
        stat = path.stat()
        
        return {
            'filename': path.name,
            'file_type': path.suffix.lower(),
            'file_size': stat.st_size,
            'created_time': stat.st_ctime,
            'modified_time': stat.st_mtime,
            'file_path': str(path.absolute())
        }
