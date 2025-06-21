import numpy as np
from typing import List, Dict, Any
from elasticsearch import Elasticsearch
from langchain_openai import OpenAIEmbeddings
import os, logging, time

class ElasticsearchHandler:
    def __init__(self, host: str = None, port: int = None, index_name: str = None):
        self.host = host or os.getenv("ELASTICSEARCH_HOST", "localhost")
        self.port = port or os.getenv("ELASTICSEARCH_PORT", "9200")
        self.index_name = index_name
        self.embedding_dim = 1536  # OpenAI embedding dimension
        self.embeddings = OpenAIEmbeddings()
        
        self._connect()
        self._setup_index()

    def _connect(self):
        """Elasticsearch 연결"""
        try:
            self.client = Elasticsearch(
                hosts=[f"http://{self.host}:{self.port}"],
                timeout=30,
                max_retries=10,
                retry_on_timeout=True
            )
            
            # 연결 확인
            if self.client.ping():
                logging.info(f"Elasticsearch에 성공적으로 연결됨: {self.host}:{self.port}")
            else:
                raise Exception("Elasticsearch 연결 실패")
        except Exception as e:
            logging.error(f"Elasticsearch 연결 실패: {e}")
            raise

    def _setup_index(self):
        """인덱스 생성 또는 확인"""
        try:
            if self.client.indices.exists(index=self.index_name):
                logging.info(f"기존 인덱스 사용: {self.index_name}")
            else:
                self._create_index()
                logging.info(f"새 인덱스 생성됨: {self.index_name}")
        except Exception as e:
            logging.error(f"인덱스 설정 실패: {e}")
            raise

    def _create_index(self):
        """Nori 토크나이저를 사용한 인덱스 생성"""
        try:
            settings = {
                "analysis": {
                    "tokenizer": {
                        "nori_user_dict": {
                            "type": "nori_tokenizer",
                            "user_dictionary": "userdict_ko.txt",
                            "decompound_mode": "mixed"
                        }
                    },
                    "analyzer": {
                        "nori_analyzer": {
                            "type": "custom",
                            "tokenizer": "nori_tokenizer",
                            "filter": [
                                "lowercase",
                                "nori_part_of_speech",
                                "nori_readingform"
                            ]
                        }
                    },
                    "filter": {
                        "nori_part_of_speech": {
                            "type": "nori_part_of_speech",
                            "stoptags": ["E", "IC", "J", "MAG", "MAJ", "MM", "SP", "SSC", "SSO", "SC", "SE", "XPN", "XSA", "XSN", "XSV", "UNA", "NA", "VSV"]
                        }
                    }
                },
                "similarity": {
                    "bm25_korean": {
                        "type": "BM25",
                        "k1": 1.2,
                        "b": 0.75
                    }
                }
            }

            mappings = {
                "properties": {
                    "content": {
                        "type": "text",
                        "analyzer": "nori_analyzer",
                        "similarity": "bm25_korean"
                    },
                    "embedding": {
                        "type": "dense_vector",
                        "dims": self.embedding_dim,
                        "index": True,
                        "similarity": "cosine"
                    },
                    "metadata": {
                        "type": "object",
                        "enabled": True
                    }
                }
            }

            # 인덱스 생성
            self.client.indices.create(
                index=self.index_name,
                settings=settings,
                mappings=mappings
            )
            
            logging.info(f"Nori 토크나이저를 사용한 인덱스 생성됨: {self.index_name}")
        except Exception as e:
            logging.error(f"인덱스 생성 실패: {e}")
            raise

    def insert_embeddings(self, contents: List[str], metadata_list: List[Dict]) -> bool:
        """문서 임베딩 생성 후 Elasticsearch에 저장"""
        try:
            # 임베딩 생성
            embeddings = self.embeddings.embed_documents(contents)
            
            # 배치 인덱싱을 위한 문서 준비
            actions = []
            for i, (content, embedding, metadata) in enumerate(zip(contents, embeddings, metadata_list)):
                doc = {
                    "_index": self.index_name,
                    "_source": {
                        "content": content,
                        "embedding": embedding,
                        "metadata": metadata
                    }
                }
                actions.append(doc)

            # 배치 인덱싱 실행
            from elasticsearch.helpers import bulk
            success, failed = bulk(self.client, actions)
            
            # 인덱스 새로고침
            self.client.indices.refresh(index=self.index_name)
            
            logging.info(f"임베딩 저장 완료: {len(contents)}개의 문서")
            return True
            
        except Exception as e:
            logging.error(f"데이터 삽입 실패: {e}")
            return False

    def search_similar(self, query_text: str, top_k: int = 5, search_type: str = "hybrid") -> List[Dict]:
        """유사도 검색 (하이브리드: 벡터 + BM25)"""
        try:
            # 쿼리 임베딩 생성
            query_embedding = self.embeddings.embed_query(query_text)
            
            if search_type == "vector":
                # 순수 벡터 검색
                query = {
                    "knn": {
                        "field": "embedding",
                        "query_vector": query_embedding,
                        "k": top_k,
                        "num_candidates": top_k * 10
                    },
                    "_source": ["content", "metadata"]
                }
            elif search_type == "bm25":
                # 순수 BM25 검색
                query = {
                    "query": {
                        "match": {
                            "content": {
                                "query": query_text,
                                "analyzer": "nori_analyzer"
                            }
                        }
                    },
                    "size": top_k,
                    "_source": ["content", "metadata"]
                }
            else:  # hybrid
                # 하이브리드 검색 (벡터 + BM25)
                query = {
                    "query": {
                        "bool": {
                            "should": [
                                {
                                    "match": {
                                        "content": {
                                            "query": query_text,
                                            "analyzer": "nori_analyzer",
                                            "boost": 1.0
                                        }
                                    }
                                }
                            ]
                        }
                    },
                    "knn": {
                        "field": "embedding",
                        "query_vector": query_embedding,
                        "k": top_k,
                        "num_candidates": top_k * 10,
                        "boost": 1.0
                    },
                    "size": top_k,
                    "_source": ["content", "metadata"]
                }

            # 검색 실행
            response = self.client.search(
                index=self.index_name,
                body=query
            )

            # 결과 처리
            search_results = []
            for hit in response['hits']['hits']:
                search_results.append({
                    "id": hit['_id'],
                    "score": hit['_score'],
                    "content": hit['_source'].get('content'),
                    "metadata": hit['_source'].get('metadata')
                })

            # 점수 기준 정렬 (높은 점수 순)
            search_results.sort(key=lambda x: x['score'], reverse=True)

            logging.info(f"유사도 검색 완료: {len(search_results)}개의 결과")
            return search_results
            
        except Exception as e:
            logging.error(f"유사도 검색 실패: {e}")
            return []

    def analyze_text(self, text: str) -> Dict:
        """Nori 토크나이저로 텍스트 분석"""
        try:
            response = self.client.indices.analyze(
                index=self.index_name,
                body={
                    "analyzer": "nori_analyzer",
                    "text": text
                }
            )
            
            tokens = [token['token'] for token in response['tokens']]
            return {
                "original": text,
                "tokens": tokens,
                "token_count": len(tokens)
            }
        except Exception as e:
            logging.error(f"텍스트 분석 실패: {e}")
            return {}

    def get_index_stats(self) -> Dict:
        """인덱스 통계 정보"""
        try:
            stats = self.client.indices.stats(index=self.index_name)
            return {
                "document_count": stats['indices'][self.index_name]['total']['docs']['count'],
                "store_size": stats['indices'][self.index_name]['total']['store']['size_in_bytes'],
                "index_name": self.index_name
            }
        except Exception as e:
            logging.error(f"인덱스 통계 조회 실패: {e}")
            return {}

    def close(self):
        """연결 종료"""
        try:
            if hasattr(self, 'client'):
                self.client.close()
            logging.info("Elasticsearch 연결 종료")
        except Exception as e:
            logging.error(f"Elasticsearch 연결 종료 실패: {e}")