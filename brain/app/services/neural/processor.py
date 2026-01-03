"""
神经感知处理器
实现从文本中提取实体和关系的神经网络处理
"""
import logging
import torch
import numpy as np
from typing import List, Dict, Any, Tuple, Optional
from pathlib import Path
from transformers import AutoTokenizer, AutoModel
from sentence_transformers import SentenceTransformer

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class NeuralProcessor:
    """
    神经感知处理器类
    集成关系提取和向量化模型
    """

    def __init__(self, device: str = "auto"):
        """
        初始化神经处理器

        Args:
            device: 计算设备 (auto, cpu, mps, cuda)
        """
        self.device = self._get_optimal_device(device)
        logger.info(f"使用设备: {self.device}")
        
        # 初始化关系提取模型
        self._init_relation_extractor()
        
        # 初始化向量化模型
        self._init_embedding_model()

    def _get_optimal_device(self, device: str) -> str:
        """
        获取最优计算设备，优先适配 Apple Silicon (M3 芯片)

        Args:
            device: 指定设备

        Returns:
            str: 优化后的设备
        """
        if device != "auto":
            return device
            
        # 检查 MPS 支持 (Apple Silicon)
        if torch.backends.mps.is_available():
            logger.info("检测到 Apple Silicon MPS 支持，使用 MPS 设备")
            return "mps"
        
        # 检查 CUDA 支持
        if torch.cuda.is_available():
            logger.info("检测到 CUDA 支持，使用 CUDA 设备")
            return "cuda"
        
        # 默认使用 CPU
        logger.info("未检测到加速设备，使用 CPU")
        return "cpu"

    def _init_relation_extractor(self):
        """
        初始化关系提取模型
        使用 Babelscape/rebel-large 模型
        """
        try:
            model_name = "Babelscape/rebel-large"
            logger.info(f"加载关系提取模型: {model_name}")
            
            # 加载模型和分词器
            self.rebel_tokenizer = AutoTokenizer.from_pretrained(model_name)
            self.rebel_model = AutoModel.from_pretrained(model_name)
            
            # 移动到指定设备
            self.rebel_model.to(self.device)
            
            logger.info("关系提取模型加载完成")
        except Exception as e:
            logger.error(f"关系提取模型加载失败: {e}")
            raise

    def _init_embedding_model(self):
        """
        初始化向量化模型
        使用 BAAI/bge-m3 模型
        """
        try:
            model_name = "BAAI/bge-m3"
            logger.info(f"加载向量化模型: {model_name}")
            
            # 加载模型
            self.embedding_model = SentenceTransformer(model_name)
            
            # 移动到指定设备
            if self.device == "mps":
                # MPS 设备需要特殊处理
                self.embedding_model = self.embedding_model.to(self.device)
            
            logger.info("向量化模型加载完成")
        except Exception as e:
            logger.error(f"向量化模型加载失败: {e}")
            raise

    def extract_triplets(self, text: str) -> List[Tuple[str, str, str]]:
        """
        从文本中提取三元组 (Subject, Relation, Object)

        Args:
            text: 输入文本

        Returns:
            List[Tuple[str, str, str]]: 提取的三元组列表
        """
        try:
            logger.info(f"开始提取关系，文本长度: {len(text)}")
            
            # 对文本进行分词
            inputs = self.rebel_tokenizer(text, return_tensors="pt", truncation=True, max_length=512)
            inputs = {k: v.to(self.device) for k, v in inputs.items()}
            
            # 使用模型进行推理
            with torch.no_grad():
                outputs = self.rebel_model(**inputs)
                
            # 解析输出为三元组
            # 注意：这里简化了实现，实际 REBEL 模型需要更复杂的解析
            # 在实际应用中，应该使用模型提供的专门解析器
            triplets = self._parse_rebel_output(outputs, text)
            
            logger.info(f"提取到 {len(triplets)} 个三元组")
            return triplets
            
        except Exception as e:
            logger.error(f"关系提取失败: {e}")
            return []

    def _parse_rebel_output(self, outputs, original_text: str) -> List[Tuple[str, str, str]]:
        """
        解析 REBEL 模型输出为三元组
        简化实现，实际应该使用专门的解析器

        Args:
            outputs: 模型输出
            original_text: 原始文本

        Returns:
            List[Tuple[str, str, str]]: 三元组列表
        """
        # 这里是一个简化的实现
        # 实际应用中应该使用 REBEL 模型提供的专门解析器
        # 或者实现基于规则的简单提取
        
        # 简单的基于规则的关系提取
        triplets = []
        
        # 示例规则：提取"我完成了X" -> (我, 完成, X)
        if "完成了" in original_text:
            parts = original_text.split("完成了")
            if len(parts) >= 2:
                subject = "我"
                object = parts[1].strip()
                triplets.append((subject, "完成", object))
        
        # 示例规则：提取"X属于Y" -> (X, 属于, Y)
        if "属于" in original_text:
            parts = original_text.split("属于")
            if len(parts) >= 2:
                object = parts[0].strip()
                subject = parts[1].strip()
                triplets.append((object, "属于", subject))
        
        # 示例规则：提取"X贡献于Y" -> (X, 贡献于, Y)
        if "贡献于" in original_text:
            parts = original_text.split("贡献于")
            if len(parts) >= 2:
                subject = parts[0].strip()
                object = parts[1].strip()
                triplets.append((subject, "贡献于", object))
        
        return triplets

    def embed_text(self, text: str) -> List[float]:
        """
        将文本转化为高维向量

        Args:
            text: 输入文本

        Returns:
            List[float]: 向量表示
        """
        try:
            logger.info(f"开始向量化，文本长度: {len(text)}")
            
            # 使用向量化模型
            with torch.no_grad():
                embedding = self.embedding_model.encode(
                    text,
                    convert_to_numpy=True,
                    normalize_embeddings=True
                )
            
            # 确保返回的是列表
            if isinstance(embedding, np.ndarray):
                embedding = embedding.tolist()
            
            logger.info(f"向量化完成，向量维度: {len(embedding)}")
            return embedding
            
        except Exception as e:
            logger.error(f"向量化失败: {e}")
            return []

    def extract_entities(self, text: str) -> List[str]:
        """
        从文本中提取实体

        Args:
            text: 输入文本

        Returns:
            List[str]: 实体列表
        """
        try:
            logger.info(f"开始提取实体，文本长度: {len(text)}")
            
            # 简单的基于规则的实体提取
            # 实际应用中应该使用专门的 NER 模型
            entities = []
            
            # 提取项目名称（简单规则）
            project_keywords = ["Endgame", "项目", "系统", "架构", "设计", "开发"]
            for keyword in project_keywords:
                if keyword in text:
                    # 提取包含关键词的短语
                    words = text.split()
                    for i, word in enumerate(words):
                        if keyword in word:
                            # 提取前后各一个词作为实体
                            start = max(0, i-1)
                            end = min(len(words), i+2)
                            entity = " ".join(words[start:end])
                            if entity and entity not in entities:
                                entities.append(entity)
            
            # 提取时间相关实体
            time_keywords = ["今天", "昨天", "明天", "2026年", "2025年", "1月", "2月"]
            for keyword in time_keywords:
                if keyword in text:
                    if keyword not in entities:
                        entities.append(keyword)
            
            logger.info(f"提取到 {len(entities)} 个实体")
            return entities
            
        except Exception as e:
            logger.error(f"实体提取失败: {e}")
            return []

    def process_text(self, text: str) -> Dict[str, Any]:
        """
        处理文本，提取三元组和实体

        Args:
            text: 输入文本

        Returns:
            Dict[str, Any]: 处理结果，包含三元组、实体和向量
        """
        try:
            logger.info(f"开始神经处理，文本长度: {len(text)}")
            
            # 提取三元组
            triplets = self.extract_triplets(text)
            
            # 提取实体
            entities = self.extract_entities(text)
            
            # 生成向量
            embedding = self.embed_text(text)
            
            result = {
                "text": text,
                "triplets": triplets,
                "entities": entities,
                "embedding": embedding
            }
            
            logger.info(f"神经处理完成，三元组: {len(triplets)}, 实体: {len(entities)}")
            return result
            
        except Exception as e:
            logger.error(f"神经处理失败: {e}")
            return {
                "text": text,
                "triplets": [],
                "entities": [],
                "embedding": [],
                "error": str(e)
            }