import logging
import os
from elasticsearch_handler import ElasticsearchHandler

# 로깅 설정
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def test_elasticsearch_handler():
    """ElasticsearchHandler 테스트"""
    
    # OpenAI API 키 확인
    if not os.getenv("OPENAI_API_KEY"):
        print("OPENAI_API_KEY 환경변수를 설정해주세요.")
        return
    
    # 핸들러 초기화
    handler = ElasticsearchHandler(
        host="localhost",
        port=9200,
        index_name="test_hybrid_search"
    )
    
    try:
        # 테스트 데이터
        test_contents = [
            "서울든든급식은 서울시 어린이들의 건강한 성장을 지원하는 급식 프로그램입니다.",
            "급식재료는 친환경 농산물을 우선적으로 사용하며, 영양사가 직접 관리합니다.",
            "어린이집과 유치원에서 든든급식 프로그램에 참여할 수 있습니다.",
            "온라인 회원가입을 통해 급식 신청과 관리가 가능합니다.",
            "식재료 주문은 매주 화요일까지 접수받으며, 목요일에 배송됩니다."
        ]
        
        test_metadata = [
            {"source": "든든급식 소개", "category": "프로그램"},
            {"source": "급식재료 정보", "category": "재료"},
            {"source": "참여기관 안내", "category": "신청"},
            {"source": "회원가입 안내", "category": "시스템"},
            {"source": "주문 프로세스", "category": "배송"}
        ]
        
        # 1. 데이터 삽입 테스트
        print("\n=== 데이터 삽입 테스트 ===")
        success = handler.insert_embeddings(test_contents, test_metadata)
        print(f"데이터 삽입 결과: {success}")
        
        # 2. 인덱스 통계 확인
        print("\n=== 인덱스 통계 ===")
        stats = handler.get_index_stats()
        print(f"통계: {stats}")
        
        # 3. 텍스트 분석 테스트
        print("\n=== Nori 토크나이저 분석 테스트 ===")
        analysis = handler.analyze_text("서울든든급식 프로그램에서 친환경 식재료를 사용합니다")
        print(f"분석 결과: {analysis}")
        
        # 4. 검색 테스트
        test_queries = [
            "서울든든급식",
            "식재료 주문",
            "어린이집",
            "회원가입"
        ]
        
        search_types = ["hybrid", "vector", "bm25"]
        
        for query in test_queries:
            print(f"\n=== '{query}' 검색 결과 ===")
            
            for search_type in search_types:
                print(f"\n--- {search_type.upper()} 검색 ---")
                results = handler.search_similar(query, top_k=3, search_type=search_type)
                
                for i, result in enumerate(results, 1):
                    print(f"{i}. 점수: {result['score']:.4f}")
                    print(f"   내용: {result['content'][:50]}...")
                    print(f"   메타데이터: {result['metadata']}")
                    print()
        
        # 5. 성능 비교
        print("\n=== 검색 방식별 성능 비교 ===")
        import time
        
        query = "든든급식 프로그램"
        
        for search_type in search_types:
            start_time = time.time()
            results = handler.search_similar(query, top_k=5, search_type=search_type)
            end_time = time.time()
            
            print(f"{search_type.upper()} 검색:")
            print(f"  - 검색 시간: {(end_time - start_time)*1000:.2f}ms")
            print(f"  - 결과 개수: {len(results)}")
            if results:
                print(f"  - 최고 점수: {results[0]['score']:.4f}")
            print()
            
    except Exception as e:
        print(f"테스트 실행 중 오류 발생: {e}")
        
    finally:
        # 연결 종료
        handler.close()

if __name__ == "__main__":
    test_elasticsearch_handler() 