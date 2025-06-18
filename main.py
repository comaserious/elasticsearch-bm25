from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from elasticsearch import Elasticsearch
from typing import List, Optional, Dict, Any
import json
import logging

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Elasticsearch BM25 Search API", version="1.0.0")

# Elasticsearch 클라이언트 초기화
es = Elasticsearch(
    hosts=["http://localhost:9200"],
    request_timeout=30,
    max_retries=3,
    retry_on_timeout=True
)

# Pydantic 모델들
class Document(BaseModel):
    id: str
    title: str
    content: str
    category: Optional[str] = None

class SearchQuery(BaseModel):
    query: str
    size: Optional[int] = 10
    category: Optional[str] = None

class SearchResult(BaseModel):
    id: str
    title: str
    content: str
    category: Optional[str] = None
    score: float

class SearchResponse(BaseModel):
    total: int
    results: List[SearchResult]
    took: int

# 인덱스 이름
INDEX_NAME = "documents"

@app.on_event("startup")
async def startup_event():
    """애플리케이션 시작 시 인덱스 생성"""
    try:
        if not es.indices.exists(index=INDEX_NAME):
            # BM25를 위한 인덱스 매핑 설정
            mapping = {
                "mappings": {
                    "properties": {
                        "title": {
                            "type": "text",
                            "analyzer": "standard",
                            "similarity": "BM25"
                        },
                        "content": {
                            "type": "text",
                            "analyzer": "standard", 
                            "similarity": "BM25"
                        },
                        "category": {
                            "type": "keyword"
                        }
                    }
                },
                "settings": {
                    "index": {
                        "similarity": {
                            "default": {
                                "type": "BM25",
                                "k1": 1.5,  # BM25 k1 파라미터
                                "b": 0.75   # BM25 b 파라미터
                            }
                        }
                    }
                }
            }
            
            es.indices.create(index=INDEX_NAME, body=mapping)
            logger.info(f"인덱스 '{INDEX_NAME}' 생성 완료")
        else:
            logger.info(f"인덱스 '{INDEX_NAME}' 이미 존재")
            
    except Exception as e:
        logger.error(f"인덱스 생성 중 오류: {e}")

@app.get("/")
async def root():
    """헬스체크 엔드포인트"""
    try:
        es_info = es.info()
        return {
            "message": "Elasticsearch BM25 API",
            "elasticsearch_status": "connected",
            "elasticsearch_version": es_info.body.get("version", {}).get("number", "unknown")
        }
    except Exception as e:
        return {
            "message": "Elasticsearch BM25 API", 
            "elasticsearch_status": "disconnected",
            "error": str(e)
        }

@app.post("/documents/", response_model=Dict[str, str])
async def add_document(document: Document):
    """문서 추가"""
    try:
        response = es.index(
            index=INDEX_NAME,
            id=document.id,
            body={
                "title": document.title,
                "content": document.content,
                "category": document.category
            }
        )
        
        # 인덱스 새로고침 (테스트용)
        es.indices.refresh(index=INDEX_NAME)
        
        return {"message": f"문서 '{document.id}' 추가 완료", "result": response.body["result"]}
    
    except Exception as e:
        logger.error(f"문서 추가 중 오류: {e}")
        raise HTTPException(status_code=500, detail=f"문서 추가 실패: {str(e)}")

@app.post("/search/", response_model=SearchResponse)
async def search_documents(search_query: SearchQuery):
    """BM25를 이용한 문서 검색"""
    try:
        # BM25 쿼리 구성
        query_body = {
            "query": {
                "bool": {
                    "must": [
                        {
                            "multi_match": {
                                "query": search_query.query,
                                "fields": ["title^2", "content"],  # title 필드에 2배 가중치
                                "type": "best_fields",
                                "fuzziness": "AUTO" # <- 퍼지 검색 설정정
                            }
                        }
                    ]
                }
            },
            "size": search_query.size,
            "_source": ["title", "content", "category"]
        }
        
        # 카테고리 필터 추가
        if search_query.category:
            query_body["query"]["bool"]["filter"] = [
                {"term": {"category": search_query.category}}
            ]
        
        # Elasticsearch 검색 실행
        response = es.search(index=INDEX_NAME, body=query_body)
        
        # 결과 파싱
        hits = response.body["hits"]
        results = []
        
        for hit in hits["hits"]:
            results.append(SearchResult(
                id=hit["_id"],
                title=hit["_source"]["title"],
                content=hit["_source"]["content"],
                category=hit["_source"].get("category"),
                score=hit["_score"]
            ))
        
        return SearchResponse(
            total=hits["total"]["value"],
            results=results,
            took=response.body["took"]
        )
        
    except Exception as e:
        logger.error(f"검색 중 오류: {e}")
        raise HTTPException(status_code=500, detail=f"검색 실패: {str(e)}")

@app.delete("/documents/{doc_id}")
async def delete_document(doc_id: str):
    """문서 삭제"""
    try:
        response = es.delete(index=INDEX_NAME, id=doc_id)
        es.indices.refresh(index=INDEX_NAME)
        return {"message": f"문서 '{doc_id}' 삭제 완료"}
    
    except Exception as e:
        logger.error(f"문서 삭제 중 오류: {e}")
        raise HTTPException(status_code=500, detail=f"문서 삭제 실패: {str(e)}")

@app.get("/documents/count")
async def get_document_count():
    """인덱스의 총 문서 수 조회"""
    try:
        response = es.count(index=INDEX_NAME)
        return {"count": response.body["count"]}
    except Exception as e:
        logger.error(f"문서 수 조회 중 오류: {e}")
        raise HTTPException(status_code=500, detail=f"문서 수 조회 실패: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 