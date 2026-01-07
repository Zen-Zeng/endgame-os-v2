"""
神经感知处理器
实现从文本中提取实体和关系的神经网络处理
支持离线模式（当无法连接 HuggingFace 时）
"""
import logging
import hashlib
from typing import List, Dict, Any, Tuple, Optional

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 可选导入
try:
    import torch
    import numpy as np
    HAS_TORCH = True
except ImportError:
    HAS_TORCH = False
    logger.warning("PyTorch 未安装，将使用离线模式")


class NeuralProcessor:
    """
    神经感知处理器类
    集成关系提取和向量化模型
    支持离线/降级模式
    """

    def __init__(self, device: str = "auto", offline_mode: bool = False):
        """
        初始化神经处理器

        Args:
            device: 计算设备 (auto, cpu, mps, cuda)
            offline_mode: 是否强制使用离线模式
        """
        self.offline_mode = offline_mode or not HAS_TORCH
        self.device = self._get_optimal_device(device)
        self.rebel_model = None
        self.rebel_tokenizer = None
        self.embedding_model = None
        
        # 模型配置
        self.rebel_model_name = "Babelscape/rebel-large"
        self.embedding_model_name = "BAAI/bge-m3"
        self.fallback_embedding_model = "sentence-transformers/all-MiniLM-L6-v2"
        
        if self.offline_mode:
            logger.info("神经处理器使用离线模式（仅使用规则和哈希）")
        else:
            logger.info(f"神经处理器初始化完成，设备: {self.device}。模型将在首次使用时加载。")

    def _get_optimal_device(self, device: str) -> str:
        """获取最优计算设备"""
        if device != "auto" or not HAS_TORCH:
            return device if HAS_TORCH else "cpu"
            
        if torch.backends.mps.is_available():
            return "mps"
        
        if torch.cuda.is_available():
            return "cuda"
        
        return "cpu"

    def _ensure_rebel_loaded(self):
        """确保关系提取模型已加载（延迟加载）"""
        if self.offline_mode or self.rebel_model is not None:
            return

        try:
            from transformers import AutoTokenizer, AutoModelForSeq2SeqLM
            logger.info(f"正在加载关系提取模型: {self.rebel_model_name}...")
            
            self.rebel_tokenizer = AutoTokenizer.from_pretrained(
                self.rebel_model_name,
                local_files_only=False
            )
            self.rebel_model = AutoModelForSeq2SeqLM.from_pretrained(
                self.rebel_model_name,
                local_files_only=False
            )
            self.rebel_model.to(self.device)
            logger.info("关系提取模型加载完成")
        except Exception as e:
            logger.warning(f"关系提取模型加载失败，切换到规则模式: {e}")
            self.offline_mode = True

    def _ensure_embedding_loaded(self):
        """确保向量化模型已加载（延迟加载，含备选方案）"""
        if self.offline_mode or self.embedding_model is not None:
            return

        try:
            from sentence_transformers import SentenceTransformer
            logger.info(f"正在加载向量化模型: {self.embedding_model_name}...")
            
            try:
                self.embedding_model = SentenceTransformer(self.embedding_model_name)
            except Exception as e:
                logger.warning(f"主向量模型加载失败，尝试轻量级备选模型 {self.fallback_embedding_model}: {e}")
                self.embedding_model = SentenceTransformer(self.fallback_embedding_model)
                
            if self.device in ["mps", "cuda"]:
                self.embedding_model = self.embedding_model.to(self.device)
            
            logger.info(f"向量化模型加载完成: {self.embedding_model.get_submodule('')}")
        except Exception as e:
            logger.warning(f"所有向量模型加载失败，切换到哈希模式: {e}")
            self.offline_mode = True

    def extract_triplets(self, text: str) -> List[Tuple[str, str, str]]:
        """从文本中提取三元组"""
        self._ensure_rebel_loaded()
        
        # 如果加载失败或处于离线模式，使用规则方法
        if self.offline_mode or self.rebel_model is None:
            return self._extract_triplets_offline(text)
            
        try:
            # REBEL 特有的处理逻辑
            inputs = self.rebel_tokenizer(text, return_tensors="pt", truncation=True, max_length=512)
            inputs = {k: v.to(self.device) for k, v in inputs.items()}
            
            with torch.no_grad():
                gen_kwargs = {
                    "max_length": 256,
                    "length_penalty": 0,
                    "num_beams": 3,
                    "num_return_sequences": 1,
                }
                generated_tokens = self.rebel_model.generate(
                    inputs["input_ids"],
                    attention_mask=inputs["attention_mask"],
                    **gen_kwargs,
                )
                
            decoded_preds = self.rebel_tokenizer.batch_decode(generated_tokens, skip_special_tokens=False)
            return self._parse_rebel_output(decoded_preds[0], text)
            
        except Exception as e:
            logger.error(f"关系提取失败: {e}")
            return self._extract_triplets_offline(text)

    def _extract_triplets_offline(self, text: str) -> List[Tuple[str, str, str]]:
        """离线模式的三元组提取（基于规则）"""
        triplets = []
        
        # 规则1: 提取"我完成了X"
        if "完成了" in text:
            parts = text.split("完成了")
            if len(parts) >= 2:
                triplets.append(("我", "完成", parts[1].strip()[:50]))
        
        # 规则2: 提取"X属于Y"
        if "属于" in text:
            parts = text.split("属于")
            if len(parts) >= 2:
                triplets.append((parts[0].strip()[:30], "属于", parts[1].strip()[:30]))
        
        # 规则3: 提取"X是Y"
        if "是" in text and len(text) > 3:
            parts = text.split("是", 1)
            if len(parts) >= 2 and len(parts[0]) > 1 and len(parts[1]) > 1:
                triplets.append((parts[0].strip()[:30], "是", parts[1].strip()[:50]))
        
        # 规则4: 提取"X想要Y"
        if "想要" in text:
            parts = text.split("想要")
            if len(parts) >= 2:
                triplets.append((parts[0].strip()[:30] or "我", "想要", parts[1].strip()[:50]))
        
        return triplets

    def _parse_rebel_output(self, text: str, original_text: str) -> List[Tuple[str, str, str]]:
        """解析 REBEL 特有的输出格式 <obj> <rel> <subj>"""
        triplets = []
        relation, subject, object_ = '', '', ''
        text = text.strip()
        current = 'x'
        for token in text.replace("<s>", "").replace("</s>", "").split():
            if token == "<triplet>":
                current = 't'
                if relation:
                    triplets.append((subject.strip(), relation.strip(), object_.strip()))
                    relation, subject, object_ = '', '', ''
                subject = ''
            elif token == "<subj>":
                current = 's'
                if relation:
                    triplets.append((subject.strip(), relation.strip(), object_.strip()))
                    relation, object_ = '', ''
                object_ = ''
            elif token == "<obj>":
                current = 'o'
                relation = ''
            else:
                if current == 't': subject += ' ' + token
                elif current == 's': object_ += ' ' + token
                elif current == 'o': relation += ' ' + token
        if relation:
            triplets.append((subject.strip(), relation.strip(), object_.strip()))
            
        # 如果模型没提取出来，用规则补齐
        if not triplets:
            return self._extract_triplets_offline(original_text)
        return triplets

    def embed_text(self, text: str) -> List[float]:
        """将文本转化为向量"""
        self._ensure_embedding_loaded()
        
        # 离线模式使用简单哈希
        if self.offline_mode or self.embedding_model is None:
            return self._embed_text_offline(text)
            
        try:
            with torch.no_grad():
                embedding = self.embedding_model.encode(
                    text,
                    convert_to_numpy=True,
                    normalize_embeddings=True
                )
            
            if isinstance(embedding, np.ndarray):
                embedding = embedding.tolist()
            
            return embedding
            
        except Exception as e:
            logger.error(f"向量化失败: {e}")
            return self._embed_text_offline(text)

    def _embed_text_offline(self, text: str) -> List[float]:
        """离线模式的文本向量化（使用哈希）"""
        # 使用 SHA256 生成伪向量
        hash_bytes = hashlib.sha256(text.encode('utf-8')).digest()
        # 转换为 384 维向量（与 BGE 模型兼容）
        vector = []
        for i in range(384):
            byte_idx = i % len(hash_bytes)
            # 归一化到 [-1, 1]
            value = (hash_bytes[byte_idx] - 128) / 128.0
            vector.append(value)
        return vector

    def extract_entities(self, text: str) -> List[str]:
        """从文本中提取实体"""
        entities = []
        
        # 关键词列表
        keywords = [
            "Endgame", "项目", "系统", "架构", "设计", "开发",
            "目标", "任务", "计划", "愿景"
        ]
        
        for keyword in keywords:
            if keyword in text:
                words = text.split()
                for i, word in enumerate(words):
                    if keyword in word:
                        start = max(0, i-1)
                        end = min(len(words), i+2)
                        entity = " ".join(words[start:end])
                        if entity and entity not in entities:
                            entities.append(entity)
        
        # 时间实体
        time_keywords = ["今天", "昨天", "明天", "2026年", "2025年"]
        for keyword in time_keywords:
            if keyword in text and keyword not in entities:
                entities.append(keyword)
        
        return entities

    def process_text(self, text: str) -> Dict[str, Any]:
        """处理文本，提取三元组、实体和向量"""
        try:
            triplets = self.extract_triplets(text)
            entities = self.extract_entities(text)
            embedding = self.embed_text(text)
            
            return {
                "text": text,
                "triplets": triplets,
                "entities": entities,
                "embedding": embedding,
                "offline_mode": self.offline_mode
            }
            
        except Exception as e:
            logger.error(f"神经处理失败: {e}")
            return {
                "text": text,
                "triplets": [],
                "entities": [],
                "embedding": self._embed_text_offline(text),
                "error": str(e),
                "offline_mode": True
            }


# 默认使用离线模式创建实例，避免启动时阻塞
def create_processor(offline_mode: bool = True) -> NeuralProcessor:
    """创建神经处理器实例"""
    return NeuralProcessor(offline_mode=offline_mode)
