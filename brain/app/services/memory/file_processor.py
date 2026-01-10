"""
文件处理器
用于解析不同格式的文件（PDF、Markdown、JSON 等）
"""
from typing import List, Dict, Any, Optional
from pathlib import Path
import json
import logging
import re
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class FileProcessor:
    """
    文件处理器类
    支持解析 PDF、Markdown、TXT、JSON 等格式
    """

    def __init__(self, chunk_size: int = 4000, chunk_overlap: int = 400):
        """
        初始化文件处理器
        chunk_size 调大以减少大文件处理时的 API 调用次数并提高吞吐量
        """
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    def parse_file(self, file_path: str) -> List[str]:
        """根据文件类型解析文件"""
        path = Path(file_path)
        if not path.exists():
            logger.error(f"文件不存在: {file_path}")
            return []

        file_extension = path.suffix.lower()
        try:
            if file_extension == '.pdf':
                return self._parse_pdf(file_path)
            elif file_extension in ['.md', '.markdown', '.txt']:
                return self._parse_text_file(file_path)
            elif file_extension == '.json':
                return self._parse_json(file_path)
            else:
                # 尝试作为纯文本读取
                return self._parse_text_file(file_path)
        except Exception as e:
            logger.error(f"解析文件失败 {file_path}: {e}")
            return []

    def _parse_pdf(self, file_path: str) -> List[str]:
        """解析 PDF 文件"""
        try:
            from pypdf import PdfReader
            reader = PdfReader(file_path)
            text = ""
            for page in reader.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
            
            return self._chunk_text(text)
        except Exception as e:
            logger.error(f"解析 PDF 失败: {e}")
            return []

    def _parse_text_file(self, file_path: str) -> List[str]:
        """通用文本文件解析 (支持大文件流式读取的思想)"""
        try:
            # 对于 50MB 以下的文件，直接读取是安全的
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                text = f.read()
            return self._chunk_text(text)
        except Exception as e:
            logger.error(f"解析文本文件失败: {e}")
            return []

    def _parse_json(self, file_path: str) -> List[str]:
        """解析 JSON 文件 (优化支持 ChatGPT 导出格式)"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            all_chunks = []
            
            # 1. 识别 ChatGPT 导出格式 (conversations.json)
            if isinstance(data, list) and len(data) > 0 and 'mapping' in data[0]:
                for conv in data:
                    title = conv.get('title', 'Untitled')
                    create_time = datetime.fromtimestamp(conv.get('create_time', 0)).strftime('%Y-%m-%d')
                    
                    # 将单个对话作为一个完整的逻辑单元处理
                    conv_texts = [f"--- 对话开始 [{create_time}] 标题: {title} ---"]
                    
                    # 按照消息创建时间排序，处理可能存在的 None 值
                    nodes = list(conv.get('mapping', {}).values())
                    def get_node_time(node):
                        msg = node.get('message')
                        if not msg: return 0
                        t = msg.get('create_time')
                        return t if isinstance(t, (int, float)) else 0
                    
                    nodes.sort(key=get_node_time)
                    
                    for node in nodes:
                        message = node.get('message')
                        if message and message.get('content') and message.get('content').get('parts'):
                            role = message.get('author', {}).get('role', 'unknown')
                            parts = message.get('content').get('parts')
                            content = " ".join([str(p) for p in parts if isinstance(p, str)])
                            if content.strip():
                                # 注入角色标记
                                prefix = "用户: " if role == "user" else "AI助手: " if role == "assistant" else f"{role}: "
                                conv_texts.append(f"{prefix}{content}")
                    
                    conv_texts.append("--- 对话结束 ---")
                    
                    # 如果对话太长，我们会在内部进行切分，但保持标题信息
                    combined_conv = "\n".join(conv_texts)
                    if len(combined_conv) > self.chunk_size:
                        # 对于长对话，按 chunk_size 切分，但每个切片都带上标题头
                        header = f"背景: {title} ({create_time})\n"
                        sub_chunks = self._chunk_text(combined_conv)
                        all_chunks.extend([header + sc if not sc.startswith("---") else sc for sc in sub_chunks])
                    else:
                        all_chunks.append(combined_conv)
            
            # 2. 通用 JSON 处理
            elif isinstance(data, list):
                for item in data:
                    all_chunks.extend(self._chunk_text(json.dumps(item, ensure_ascii=False)))
            else:
                all_chunks.extend(self._chunk_text(json.dumps(data, ensure_ascii=False)))
            
            return all_chunks
        except Exception as e:
            logger.error(f"解析 JSON 失败: {e}")
            return []

    def _chunk_text(self, text: str) -> List[str]:
        """将长文本切分为片段，优先在换行符处切分"""
        if not text:
            return []
            
        chunks = []
        start = 0
        text_len = len(text)
        
        while start < text_len:
            # 确定当前切片的理论终点
            end = start + self.chunk_size
            
            if end < text_len:
                # 尝试在 chunk_size 范围内寻找最后一个换行符
                # 寻找范围限制在切片的后半部分，避免切片太短
                search_start = start + self.chunk_size // 2
                last_newline = text.rfind('\n', search_start, end)
                
                if last_newline != -1:
                    end = last_newline + 1 # 包含换行符
            
            chunk = text[start:end].strip()
            if chunk:
                chunks.append(chunk)
            
            # 移动起点，考虑重叠
            start = end - self.chunk_overlap
            
            # 边界处理：如果剩余内容太少，直接结束
            if start >= text_len or (text_len - start) < self.chunk_size // 4:
                if start < text_len:
                    last_chunk = text[start:].strip()
                    if last_chunk: chunks.append(last_chunk)
                break
                
        return chunks

    def split_chat_log(self, file_path: str) -> List[Dict[str, Any]]:
        """
        解析 ChatGPT/Gemini 原始 JSON 并拆分为多个对话
        返回对话列表，每个对话包含标题、内容和建议的文件名
        """
        path = Path(file_path)
        if not path.exists():
            return []

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            conversations = []

            # 1. 处理 ChatGPT 格式 (list of dicts with 'mapping')
            if isinstance(data, list) and len(data) > 0 and 'mapping' in data[0]:
                for conv in data:
                    title = conv.get('title') or "未命名对话"
                    create_time_ts = conv.get('create_time', 0)
                    create_time = datetime.fromtimestamp(create_time_ts).strftime('%Y%m%d_%H%M%S')
                    
                    # 提取消息文本
                    messages = []
                    mapping = conv.get('mapping', {})
                    # 简单排序
                    sorted_nodes = sorted(
                        mapping.values(), 
                        key=lambda x: (x.get('message', {}) or {}).get('create_time') or 0
                    )
                    
                    for node in sorted_nodes:
                        msg = node.get('message')
                        if not msg: continue
                        role = msg.get('author', {}).get('role')
                        content_parts = msg.get('content', {}).get('parts', [])
                        text = "".join([p if isinstance(p, str) else "" for p in content_parts])
                        if text:
                            messages.append({"role": role, "content": text})
                    
                    if messages:
                        # 生成安全的文件名
                        safe_title = re.sub(r'[\\/*?:"<>|]', "", title).replace(" ", "_")[:50]
                        filename = f"chatgpt_{create_time}_{safe_title}.json"
                        
                        conversations.append({
                            "title": title,
                            "filename": filename,
                            "create_time": datetime.fromtimestamp(create_time_ts).isoformat(),
                            "content": {
                                "source": "chatgpt_export",
                                "title": title,
                                "created_at": datetime.fromtimestamp(create_time_ts).isoformat(),
                                "messages": messages
                            }
                        })

            # 2. 处理 Gemini 格式 (通常是一个包含 'conversations' 键的对象或列表)
            elif isinstance(data, dict) and 'conversations' in data:
                # 适配 Gemini 导出 (Google Takeout)
                for conv in data['conversations']:
                    title = conv.get('title') or "Gemini 对话"
                    # Gemini 格式通常是 messages: [{author: "user", content: "..."}]
                    raw_messages = conv.get('messages', [])
                    messages = []
                    
                    for msg in raw_messages:
                        role = msg.get('author', 'unknown')
                        content = msg.get('content', '')
                        if content:
                            messages.append({"role": role, "content": content})
                    
                    if messages:
                        # 尝试获取时间戳，如果没有则用当前时间
                        create_time = datetime.now().strftime('%Y%m%d_%H%M%S')
                        safe_title = re.sub(r'[\\/*?:"<>|]', "", title).replace(" ", "_")[:50]
                        filename = f"gemini_{create_time}_{safe_title}.json"
                        
                        conversations.append({
                            "title": title,
                            "filename": filename,
                            "content": {
                                "source": "gemini_export",
                                "title": title,
                                "created_at": create_time,
                                "messages": messages
                            }
                        })
            
            # 3. 处理 Gemini 列表格式 (如果是直接导出的数组)
            elif isinstance(data, list) and len(data) > 0 and 'messages' in data[0] and 'title' in data[0]:
                for conv in data:
                    title = conv.get('title') or "Gemini 对话"
                    raw_messages = conv.get('messages', [])
                    messages = []
                    for msg in raw_messages:
                        role = msg.get('author', 'unknown')
                        content = msg.get('content', '')
                        if content:
                            messages.append({"role": role, "content": content})
                    
                    if messages:
                        create_time = datetime.now().strftime('%Y%m%d_%H%M%S')
                        safe_title = re.sub(r'[\\/*?:"<>|]', "", title).replace(" ", "_")[:50]
                        filename = f"gemini_{create_time}_{safe_title}.json"
                        conversations.append({
                            "title": title,
                            "filename": filename,
                            "content": {
                                "source": "gemini_export",
                                "title": title,
                                "created_at": create_time,
                                "messages": messages
                            }
                        })

            # 4. 处理 Google My Activity 格式 (Gemini Apps)
            elif isinstance(data, list) and len(data) > 0 and 'header' in data[0] and data[0].get('header') == 'Gemini Apps':
                # My Activity 是扁平的，每一条是一个 Prompt + Response
                # 我们按时间排序并尝试简单的会话合并（可选），或者暂时每条作为一个独立对话
                for activity in data:
                    raw_title = activity.get('title', '')
                    if not raw_title.startswith('Prompted '):
                        continue
                    
                    user_prompt = raw_title.replace('Prompted ', '', 1).strip()
                    
                    # 提取 AI 回复
                    ai_response = ""
                    safe_items = activity.get('safeHtmlItem', [])
                    if safe_items and 'html' in safe_items[0]:
                        html_content = safe_items[0]['html']
                        # 简单去除 HTML 标签
                        ai_response = re.sub(r'<[^>]+>', '', html_content)
                        # 处理常见的实体编码
                        ai_response = ai_response.replace('&nbsp;', ' ').replace('&lt;', '<').replace('&gt;', '>').replace('&amp;', '&').replace('&quot;', '"').replace('&#39;', "'")
                    
                    if user_prompt or ai_response:
                        messages = []
                        if user_prompt:
                            messages.append({"role": "user", "content": user_prompt})
                        if ai_response:
                            messages.append({"role": "model", "content": ai_response})
                        
                        # 提取一个更短的标题
                        display_title = user_prompt[:40].strip() + "..." if len(user_prompt) > 40 else user_prompt
                        if not display_title: display_title = "Gemini 活动记录"
                        
                        create_time_str = activity.get('time', datetime.now().isoformat())
                        # 转换时间戳为安全文件名
                        try:
                            # 2026-01-09T04:29:28.069Z
                            clean_time = create_time_str.replace('Z', '').split('.')[0]
                            dt = datetime.fromisoformat(clean_time)
                            file_ts = dt.strftime('%Y%m%d_%H%M%S')
                        except:
                            file_ts = datetime.now().strftime('%Y%m%d_%H%M%S')

                        safe_title = re.sub(r'[\\/*?:"<>|]', "", display_title).replace(" ", "_")[:30]
                        filename = f"gemini_activity_{file_ts}_{safe_title}.json"
                        
                        conversations.append({
                            "title": display_title,
                            "filename": filename,
                            "create_time": create_time_str,
                            "content": {
                                "source": "gemini_activity",
                                "title": display_title,
                                "created_at": create_time_str,
                                "messages": messages
                            }
                        })

            return conversations
        except Exception as e:
            logger.error(f"拆分聊天记录失败: {e}")
            return []

    def get_file_metadata(self, file_path: str) -> Dict[str, Any]:
        """获取文件元数据"""
        path = Path(file_path)
        return {
            "filename": path.name,
            "extension": path.suffix,
            "size": path.stat().st_size,
            "processed_at": datetime.now().isoformat()
        }
