# LLM Wiki

> Karpathy의 [llm-wiki](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f) 패턴을 웹서비스로 확장한 시스템.
> 사용자가 게시판으로 자료를 올리면 LLM이 점진적으로 위키를 빌드·유지하며, 채팅으로 질의하고 lint로 건강도를 점검합니다.

## 핵심 개념

RAG와 다르게, **위키는 매 쿼리마다 재생성하지 않고 영구적으로 누적·유지되는 산출물(persistent compounding artifact)** 입니다.

| 계층 | 설명 | 소유자 |
|---|---|---|
| Raw | 사용자가 올린 ingest 게시글·이미지 | 사람 |
| Wiki | LLM이 생성·유지하는 markdown 페이지 트리 | LLM |
| Schema | 위키 구조·작성 규칙·프롬프트 | 관리자 |

## 기술 스택

| 영역 | 스택 |
|---|---|
| Frontend | Vue 3 + TypeScript, Tailwind CSS, Ant Design Vue |
| Backend | FastAPI (Python 3.11+) |
| ORM / Migration | SQLAlchemy 2.x + Alembic |
| LLM | vLLM (OpenAI 호환 엔드포인트) |
| Scheduler | Apache Airflow |
| DB | MySQL 8.0 / MariaDB 11+ |
| File Storage | 로컬 파일시스템 (`./storage/`) |
| Wiki Storage | Git 저장소 (`./wiki_repo/`) |

## 빠른 시작

### 1. 사전 요구사항

- Python 3.11+ (conda `llm` 환경 권장)
- Node.js 20+
- MySQL 8.0 또는 MariaDB 11+
- vLLM 서버 (선택 — 없으면 ingest/채팅 기능 비활성)

### 2. 환경 설정

```bash
cp .env.example .env
```

`.env` 파일에서 아래 항목을 환경에 맞게 수정합니다:

```env
DATABASE_URL=mysql+pymysql://user01:yourpassword@localhost:3306/llmwiki
SECRET_KEY=your-secret-key-here
VLLM_BASE_URL=http://your-vllm-server/v1
```

### 3. DB 생성 및 마이그레이션

```bash
# DB 생성
mysql -u user01 -p -e "CREATE DATABASE IF NOT EXISTS llmwiki CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"

# Python 의존성 설치
conda activate llm
pip install -r requirements.txt

# 마이그레이션 실행
alembic upgrade head

# 초기 시드 (admin 계정 생성)
python scripts/apply_seed.py
# 또는
mysql -u user01 -p llmwiki < scripts/seed.sql
```

초기 관리자 계정: `admin@llmwiki.local` / `admin1234`

### 4. 백엔드 시작

```bash
cd backend
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

API 문서: http://localhost:8000/api/docs

### 5. 프론트엔드 시작

```bash
cd frontend
npm install
npm run dev
```

앱: http://localhost:5173

## 디렉토리 구조

```
.
├── frontend/                     # Vue 3 + TypeScript SPA
│   └── src/
│       ├── pages/
│       │   ├── IngestBoard/      # 게시판 (목록/상세/에디터)
│       │   ├── WikiBrowse/       # 위키 탐색 (트리+뷰어+검색)
│       │   ├── Chat/             # LLM 채팅 (SSE 스트리밍)
│       │   ├── LintDashboard/    # Lint 결과 대시보드
│       │   └── SchemaAdmin/      # Schema 관리 (admin 전용)
│       ├── components/           # AppLayout, StatusBadge, Timeline, MarkdownRender
│       ├── api/                  # Axios 클라이언트 + 타입
│       └── stores/               # Pinia (auth, ingest)
│
├── backend/
│   ├── app/                      # FastAPI 앱
│   │   ├── api/                  # 라우터 (auth/ingest/wiki/chat/lint/files/schema)
│   │   ├── core/                 # config, security, deps, database
│   │   ├── models/               # SQLAlchemy 2.x ORM 모델
│   │   └── schemas/              # Pydantic 스키마
│   └── wiki_pipeline/            # LLM 파이프라인 핵심 (DAG·API 공용)
│       ├── ingest.py             # ingest_post() — 9단계 흐름
│       ├── lint.py               # 5종 lint 검사
│       ├── llm_client.py         # vLLM wrapper (ingest/lint/chat 모델 라우팅)
│       ├── wiki_repo.py          # Git + markdown I/O
│       ├── storage.py            # 로컬 FS (path traversal 방지)
│       ├── ocr.py                # OCR (Phase 3)
│       └── prompts/              # 시스템 프롬프트 5종
│
├── dags/                         # Airflow DAG
│   ├── wiki_ingest_daily.py      # 매일 02:00 — OCR 병렬 + Ingest 순차
│   └── wiki_lint_weekly.py       # 매주 일요일 03:00 — Lint 4종 병렬
│
├── alembic/                      # DB 마이그레이션
├── storage/                      # 첨부파일 (gitignore)
├── wiki_repo/                    # 위키 git 저장소
├── tests/                        # 단위 테스트
├── docker-compose.yml
├── .env.example
└── requirements.txt
```

## API 엔드포인트 개요

| 메서드 | 경로 | 설명 |
|---|---|---|
| POST | `/api/auth/login` | JSON 로그인 → JWT |
| GET | `/api/auth/me` | 현재 유저 정보 |
| GET | `/api/ingest/posts` | 게시글 목록 (상태/카테고리 필터) |
| POST | `/api/ingest/posts` | 게시글 작성 |
| GET | `/api/ingest/posts/{id}` | 상세 (타임라인 + LLM 로그 + 결과 위키) |
| POST | `/api/ingest/posts/{id}/run` | 즉시 처리 |
| POST | `/api/ingest/posts/{id}/retry` | 재시도 |
| GET | `/api/wiki/pages` | 위키 페이지 목록 |
| GET | `/api/wiki/pages/by-path` | 페이지 본문 |
| GET | `/api/wiki/search?q=` | 전문 검색 (FULLTEXT / LIKE 폴백) |
| POST | `/api/chat/sessions/{id}/messages` | 채팅 SSE 스트리밍 |
| POST | `/api/chat/sessions/{id}/to-ingest` | 대화 → Ingest 변환 |
| GET | `/api/lint/findings` | Lint 결과 목록 |
| POST | `/api/lint/run` | 수동 Lint 실행 (admin) |
| GET/PUT | `/api/schema/current` | Schema 조회/수정 (admin) |

전체 스펙: http://localhost:8000/api/docs

## Ingest 처리 흐름

```
사용자 게시글 작성
    ↓
[Airflow: wiki_ingest_daily / 즉시 처리]
    ↓
OCR (이미지 첨부 시)
    ↓
LLM이 위키 인덱스 분석 → 영향 페이지 식별
    ↓
각 페이지 현재 내용 읽기 → 새 markdown 생성
    ↓
출처 섹션 자동 추가 (## 출처)
    ↓
wiki_pages / wiki_page_sources / wiki_backlinks DB 갱신
    ↓
index.md / log.md 갱신 → git commit
```

## Lint 검사 항목

| 타입 | 설명 |
|---|---|
| `orphan` | 백링크가 없는 고아 페이지 |
| `broken_link` | `[[링크]]` 대상이 존재하지 않는 경우 |
| `missing_entity` | 본문에 언급되지만 페이지가 없는 개념 |
| `stale` | 90일 이상 미갱신 페이지 |
| `contradiction` | LLM이 감지한 페이지 간 모순 (비용 높음, opt-in) |

## 권한 구조

| 역할 | 권한 |
|---|---|
| `admin` | 전체 (Schema 수정, Lint 실행, 사용자 관리) |
| `editor` | 게시글 작성·수정, 채팅 |
| `viewer` | 읽기 전용 |

## Airflow DAG 설정

```bash
# AIRFLOW_HOME을 프로젝트 내로 설정
export AIRFLOW_HOME=$(pwd)/airflow_home
export AIRFLOW__CORE__DAGS_FOLDER=$(pwd)/dags

# DB 초기화 및 시작
airflow db init
airflow webserver &
airflow scheduler &
```

`AIRFLOW__CORE__DAGS_FOLDER` 에 `dags/` 경로를 지정하거나 기존 Airflow의 dags 폴더에 심볼릭 링크를 추가하세요.

## 보안 고려사항

- **파일 업로드**: UUID 파일명 + 확장자 화이트리스트 (png/jpg/pdf/txt/md 등) + path traversal 방지
- **Wiki 직접 수정 금지**: 사용자에게 read-only API만 노출, 수정은 ingest 경유
- **채팅 Hallucination 방지**: wiki 인용 없는 주장 → `unverified=TRUE` 플래그 강제
- **출처 추적**: `wiki_page_sources` 테이블 + 페이지 하단 `## 출처` 자동 추가
- **인증**: JWT Bearer 토큰, bcrypt 패스워드 해시

## 알려진 제약 및 향후 계획

### 현재 제약
- **MariaDB**: `WITH PARSER ngram` 미지원으로 한글 FULLTEXT 검색 품질 제한. MySQL 8.0 전환 권장.
- **OCR**: Phase 1 stub. PaddleOCR / vision LLM은 Phase 3에서 추가.
- **`[[위키링크]]`**: 현재 굵게 렌더링만. Phase 2에서 vue-router 클릭 라우팅 추가 예정.
- **Airflow**: Windows 환경에서는 WSL 또는 Docker 사용 권장.

### Phase 2 예정
- `[[위키링크]]` → vue-router 클릭 라우팅
- 그래프 뷰 (vis-network)
- OCR 이미지 처리 (PaddleOCR / vision LLM)

### Phase 3 예정
- Meilisearch / Typesense 도입 (한국어 검색 품질 개선)
- 벡터 임베딩 검색 (bge-m3)
- 파일 스토리지 MinIO/S3 마이그레이션 대비

## 개발 참고

```bash
# 테스트 실행
conda activate llm
pytest tests/ -v

# 타입 체크 (프론트엔드)
cd frontend && npx vue-tsc --noEmit

# Alembic 새 마이그레이션 생성
alembic revision --autogenerate -m "description"
```
