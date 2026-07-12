"""工具函数

提供文本处理和搜索相关的工具函数：
- 分词处理（jieba）
- TF-IDF 计算
- 余弦相似度计算
- 基于相似度的搜索功能
"""
import jieba
import math
from collections import defaultdict


def tokenize(text):
    """使用 jieba 分词，过滤空白字符"""
    return [word for word in jieba.lcut(text) if word.strip()]


def compute_tf(tokens):
    """计算词频（TF）"""
    tf = defaultdict(int)
    total = len(tokens)
    for token in tokens:
        tf[token] += 1
    for token in tf:
        tf[token] /= total
    return tf


def compute_idf(documents):
    """计算逆文档频率（IDF）"""
    idf = {}
    total_docs = len(documents)
    all_tokens = set()
    for doc in documents:
        all_tokens.update(tokenize(doc))
    
    for token in all_tokens:
        doc_count = sum(1 for doc in documents if token in tokenize(doc))
        idf[token] = math.log((total_docs + 1) / (doc_count + 1)) + 1
    return idf


def compute_tfidf(tokens, idf):
    """计算 TF-IDF 向量"""
    tf = compute_tf(tokens)
    tfidf = {}
    for token in tf:
        if token in idf:
            tfidf[token] = tf[token] * idf[token]
    return tfidf


def cosine_similarity(vec1, vec2):
    """计算两个向量的余弦相似度"""
    all_tokens = set(vec1.keys()) | set(vec2.keys())
    dot_product = sum(vec1.get(token, 0) * vec2.get(token, 0) for token in all_tokens)
    norm1 = math.sqrt(sum(v**2 for v in vec1.values()))
    norm2 = math.sqrt(sum(v**2 for v in vec2.values()))
    if norm1 == 0 or norm2 == 0:
        return 0.0
    return dot_product / (norm1 * norm2)
