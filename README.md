# Elasticsearch BM25 검색 API

FastAPI와 Elasticsearch를 이용한 BM25 검색 엔진 구현 프로젝트입니다.

## 🚀 프로젝트 개요

이 프로젝트는 Elasticsearch의 BM25 알고리즘을 활용하여 고성능 검색 기능을 제공하는 REST API를 구현합니다.

### 주요 기능

- **BM25 검색 알고리즘**: 확률 기반 순위 함수로 정확한 검색 결과 제공
- **FastAPI 백엔드**: 고성능 비동기 웹 프레임워크
- **실시간 검색**: Elasticsearch 기반 실시간 문서 검색
- **카테고리 필터링**: 문서 카테고리별 검색 지원
- **퍼지 검색**: 오타 허용 검색 기능
- **필드 가중치**: 제목 필드에 더 높은 가중치 부여

## 📋 요구사항

- Python 3.8+
- Docker & Docker Compose
- Elasticsearch 9.0.2

## 🛠️ 설치 및 실행

### 1. 저장소 클론 및 의존성 설치

```bash
# 의존성 패키지 설치
pip install -r requirements.txt
```

### 2. Elasticsearch 실행

```bash
# Docker Compose로 Elasticsearch 실행
docker-compose up -d

# Elasticsearch 상태 확인
curl http://localhost:9200
```

### 3. FastAPI 서버 실행

```bash
# 개발 서버 실행
python main.py

# 또는 uvicorn 직접 실행
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### 4. API 문서 확인

브라우저에서 다음 URL로 접속:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## 🧪 테스트 실행

### pytest를 이용한 자동 테스트

```bash
# 모든 테스트 실행
pytest test_bm25.py -v

# 특정 테스트만 실행
pytest test_bm25.py::TestBM25Search::test_basic_search -v

# 성능 테스트 실행
python test_bm25.py
```

### 수동 API 테스트

```bash
# 헬스체크
curl http://localhost:8000/

# 문서 추가
curl -X POST "http://localhost:8000/documents/" \
  -H "Content-Type: application/json" \
  -d '{
    "id": "test1",
    "title": "테스트 문서",
    "content": "이것은 테스트용 문서입니다.",
    "category": "test"
  }'

# 문서 검색
curl -X POST "http://localhost:8000/search/" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "테스트",
    "size": 5
  }'
```

## 📊 API 엔드포인트

### 문서 관리

- `POST /documents/` - 문서 추가
- `DELETE /documents/{doc_id}` - 문서 삭제
- `GET /documents/count` - 문서 수 조회

### 검색

- `POST /search/` - BM25 검색 수행
  - `query`: 검색어 (필수)
  - `size`: 결과 개수 (기본값: 10)
  - `category`: 카테고리 필터 (선택)

### 헬스체크

- `GET /` - 서버 및 Elasticsearch 상태 확인

## 🔧 BM25 설정

Elasticsearch 인덱스 설정에서 BM25 파라미터를 조정할 수 있습니다:

```json
{
  "settings": {
    "index": {
      "similarity": {
        "default": {
          "type": "BM25",
          "k1": 1.5,    // 텀 빈도 포화점
          "b": 0.75     // 문서 길이 정규화 정도
        }
      }
    }
  }
}
```

### BM25 파라미터 설명

- **k1** (기본값: 1.5): 텀 빈도의 포화점을 조정
  - 높을수록 텀 빈도가 점수에 더 큰 영향
- **b** (기본값: 0.75): 문서 길이 정규화 정도
  - 0에 가까울수록 문서 길이 무시
  - 1에 가까울수록 문서 길이를 많이 고려

## 📈 테스트 결과

테스트 코드는 다음 항목들을 검증합니다:

- ✅ 서버 연결 및 헬스체크
- ✅ 기본 BM25 검색 기능
- ✅ 관련도 순위 정렬
- ✅ 제목 필드 가중치 적용
- ✅ 카테고리 필터링
- ✅ 퍼지 검색 (오타 허용)
- ✅ 다중 키워드 검색
- ✅ 성능 측정

## 🎯 사용 예시

```python
import httpx

client = httpx.Client(base_url="http://localhost:8000")

# 문서 추가
document = {
    "id": "python_guide",
    "title": "Python 완전 정복 가이드",
    "content": "Python 프로그래밍의 모든 것을 다루는 완전한 가이드입니다.",
    "category": "programming"
}
response = client.post("/documents/", json=document)

# 검색 수행
search_query = {
    "query": "Python 프로그래밍",
    "size": 10,
    "category": "programming"
}
response = client.post("/search/", json=search_query)
results = response.json()

print(f"총 {results['total']}개 문서 발견")
for result in results['results']:
    print(f"- {result['title']} (점수: {result['score']:.2f})")
```

## 🔍 주의사항

1. **Elasticsearch 메모리**: 운영 환경에서는 충분한 메모리 할당 필요
2. **인덱스 새로고침**: 실시간 검색을 위해 테스트에서 인덱스 새로고침 사용
3. **보안 설정**: 운영 환경에서는 Elasticsearch 보안 설정 필수
4. **모니터링**: 검색 성능과 Elasticsearch 클러스터 상태 모니터링 권장

## 📝 라이선스

MIT License 