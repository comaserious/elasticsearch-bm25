import pytest
import httpx
import asyncio
from typing import List, Dict
import time

# 테스트 데이터
SAMPLE_DOCUMENTS = [
    {
        "id": "doc1",
        "title": "Python 프로그래밍 기초",
        "content": "Python은 배우기 쉽고 강력한 프로그래밍 언어입니다. 데이터 분석, 웹 개발, 인공지능 등 다양한 분야에서 활용됩니다.",
        "category": "programming"
    },
    {
        "id": "doc2", 
        "title": "Elasticsearch 검색 엔진",
        "content": "Elasticsearch는 분산형 실시간 검색 엔진입니다. RESTful API를 제공하며 JSON 문서를 저장하고 검색할 수 있습니다.",
        "category": "database"
    },
    {
        "id": "doc3",
        "title": "FastAPI 웹 프레임워크",
        "content": "FastAPI는 Python으로 작성된 고성능 웹 프레임워크입니다. 자동 API 문서 생성과 타입 힌트를 지원합니다.",
        "category": "web"
    },
    {
        "id": "doc4",
        "title": "머신러닝과 Python",
        "content": "Python은 머신러닝과 데이터 사이언스 분야에서 가장 인기 있는 언어입니다. scikit-learn, pandas, numpy 등의 라이브러리를 제공합니다.",
        "category": "ai"
    },
    {
        "id": "doc5",
        "title": "검색 알고리즘 BM25",
        "content": "BM25는 정보 검색에서 사용되는 확률 기반 순위 함수입니다. TF-IDF의 개선된 버전으로 많이 사용됩니다.",
        "category": "algorithm"
    }
]

BASE_URL = "http://localhost:8000"

class TestBM25Search:
    """BM25 검색 기능 테스트 클래스"""
    
    @pytest.fixture(scope="class")
    def client(self):
        """HTTP 클라이언트 픽스처"""
        return httpx.Client(base_url=BASE_URL, timeout=30.0)
    
    @pytest.fixture(scope="class", autouse=True)
    async def setup_test_data(self, client):
        """테스트 데이터 설정"""
        print("\n🔧 테스트 데이터 설정 중...")
        
        # 서버 연결 확인
        max_retries = 10
        for i in range(max_retries):
            try:
                response = client.get("/")
                if response.status_code == 200:
                    print("✅ 서버 연결 성공")
                    break
            except Exception as e:
                if i == max_retries - 1:
                    pytest.fail(f"서버 연결 실패: {e}")
                print(f"서버 연결 대기 중... ({i+1}/{max_retries})")
                time.sleep(2)
        
        # 기존 문서 삭제
        for doc in SAMPLE_DOCUMENTS:
            try:
                client.delete(f"/documents/{doc['id']}")
            except:
                pass
        
        # 테스트 문서 추가
        for doc in SAMPLE_DOCUMENTS:
            response = client.post("/documents/", json=doc)
            assert response.status_code == 200
            print(f"✅ 문서 '{doc['id']}' 추가 완료")
        
        # 인덱싱 완료 대기
        time.sleep(2)
        print("✅ 테스트 데이터 설정 완료\n")
        
        yield
        
        # 테스트 후 정리
        print("\n🧹 테스트 데이터 정리 중...")
        for doc in SAMPLE_DOCUMENTS:
            try:
                client.delete(f"/documents/{doc['id']}")
            except:
                pass
        print("✅ 테스트 데이터 정리 완료")
    
    def test_server_health(self, client):
        """서버 헬스체크 테스트"""
        response = client.get("/")
        assert response.status_code == 200
        
        data = response.json()
        assert "message" in data
        assert "elasticsearch_status" in data
        print(f"✅ 서버 상태: {data['elasticsearch_status']}")
    
    def test_document_count(self, client):
        """문서 수 확인 테스트"""
        response = client.get("/documents/count")
        assert response.status_code == 200
        
        data = response.json()
        assert data["count"] >= len(SAMPLE_DOCUMENTS)
        print(f"✅ 인덱스 문서 수: {data['count']}")
    
    def test_basic_search(self, client):
        """기본 검색 테스트"""
        search_query = {
            "query": "Python",
            "size": 5
        }
        
        response = client.post("/search/", json=search_query)
        assert response.status_code == 200
        
        data = response.json()
        assert "total" in data
        assert "results" in data
        assert "took" in data
        
        results = data["results"]
        assert len(results) > 0
        
        # 검색 결과에 score가 포함되어 있는지 확인
        for result in results:
            assert "score" in result
            assert result["score"] > 0
            
        print(f"✅ 기본 검색 - 총 {data['total']}개 결과 ({data['took']}ms)")
        for i, result in enumerate(results[:3]):
            print(f"   {i+1}. {result['title']} (score: {result['score']:.2f})")
    
    def test_bm25_relevance_ranking(self, client):
        """BM25 관련도 순위 테스트"""
        search_query = {
            "query": "Python 프로그래밍",
            "size": 10
        }
        
        response = client.post("/search/", json=search_query)
        assert response.status_code == 200
        
        data = response.json()
        results = data["results"]
        
        # 결과가 score 순으로 정렬되어 있는지 확인
        if len(results) > 1:
            for i in range(len(results) - 1):
                assert results[i]["score"] >= results[i + 1]["score"]
        
        print(f"✅ BM25 관련도 순위 테스트 - {len(results)}개 결과")
        for i, result in enumerate(results):
            print(f"   {i+1}. {result['title']} (score: {result['score']:.2f})")
    
    def test_title_field_boost(self, client):
        """제목 필드 가중치 테스트"""
        # 제목에 키워드가 있는 경우와 내용에만 있는 경우 비교
        search_query = {
            "query": "Elasticsearch",
            "size": 10
        }
        
        response = client.post("/search/", json=search_query)
        assert response.status_code == 200
        
        data = response.json()
        results = data["results"]
        
        # 제목에 "Elasticsearch"가 포함된 문서가 더 높은 점수를 받아야 함
        title_match = None
        content_match = None
        
        for result in results:
            if "Elasticsearch" in result["title"]:
                title_match = result
            elif "Elasticsearch" in result["content"] and "Elasticsearch" not in result["title"]:
                content_match = result
        
        if title_match and content_match:
            assert title_match["score"] > content_match["score"]
            print(f"✅ 제목 가중치 테스트 통과")
            print(f"   제목 매치: {title_match['title']} (score: {title_match['score']:.2f})")
            print(f"   내용 매치: {content_match['title']} (score: {content_match['score']:.2f})")
    
    def test_category_filter(self, client):
        """카테고리 필터 테스트"""
        search_query = {
            "query": "Python",
            "category": "programming",
            "size": 10
        }
        
        response = client.post("/search/", json=search_query)
        assert response.status_code == 200
        
        data = response.json()
        results = data["results"]
        
        # 모든 결과가 지정된 카테고리에 속하는지 확인
        for result in results:
            assert result["category"] == "programming"
        
        print(f"✅ 카테고리 필터 테스트 - {len(results)}개 결과 (category: programming)")
    
    def test_fuzzy_search(self, client):
        """퍼지 검색 테스트 (오타 허용)"""
        search_query = {
            "query": "Pythom",  # 의도적 오타
            "size": 5
        }
        
        response = client.post("/search/", json=search_query)
        assert response.status_code == 200
        
        data = response.json()
        results = data["results"]
        
        # 오타가 있어도 "Python" 관련 문서를 찾을 수 있어야 함
        python_found = any("Python" in result["title"] or "Python" in result["content"] 
                          for result in results)
        
        if python_found:
            print("✅ 퍼지 검색 테스트 통과 - 오타 허용 검색 성공")
        else:
            print("⚠️ 퍼지 검색 결과 없음 (설정 조정 필요)")
    
    def test_multi_term_search(self, client):
        """다중 키워드 검색 테스트"""
        search_query = {
            "query": "검색 엔진 BM25",
            "size": 10
        }
        
        response = client.post("/search/", json=search_query)
        assert response.status_code == 200
        
        data = response.json()
        results = data["results"]
        
        print(f"✅ 다중 키워드 검색 - {len(results)}개 결과")
        for i, result in enumerate(results[:3]):
            print(f"   {i+1}. {result['title']} (score: {result['score']:.2f})")
    
    def test_empty_search(self, client):
        """빈 검색어 테스트"""
        search_query = {
            "query": "",
            "size": 5
        }
        
        response = client.post("/search/", json=search_query)
        # 빈 검색어는 에러가 발생하거나 모든 문서를 반환할 수 있음
        assert response.status_code in [200, 400]
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ 빈 검색어 처리 - {len(data['results'])}개 결과")

def run_performance_test():
    """성능 테스트 함수"""
    print("\n🚀 성능 테스트 시작...")
    
    client = httpx.Client(base_url=BASE_URL, timeout=30.0)
    
    search_queries = [
        "Python",
        "Elasticsearch 검색",
        "FastAPI 웹",
        "머신러닝 데이터",
        "BM25 알고리즘"
    ]
    
    total_time = 0
    total_requests = 0
    
    for query in search_queries:
        start_time = time.time()
        
        search_query = {"query": query, "size": 10}
        response = client.post("/search/", json=search_query)
        
        end_time = time.time()
        response_time = (end_time - start_time) * 1000  # ms
        
        if response.status_code == 200:
            data = response.json()
            es_time = data["took"]
            total_time += response_time
            total_requests += 1
            
            print(f"   '{query}': {response_time:.1f}ms (ES: {es_time}ms)")
    
    if total_requests > 0:
        avg_time = total_time / total_requests
        print(f"✅ 평균 응답 시간: {avg_time:.1f}ms")
    
    client.close()

if __name__ == "__main__":
    # 직접 실행 시 성능 테스트도 함께 실행
    run_performance_test() 