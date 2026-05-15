# Notion 학습 대시보드 자동화 프로그램

Python과 Notion API를 사용해서 Notion 학습 대시보드에 과제, 프로젝트, 공부 기록을 추가하고 마감 임박 과제를 조회하는 프로그램입니다.

## 파일 구성

- `main.py`: 프로그램 실행 파일
- `.env`: Notion API 키와 데이터베이스 ID 저장 파일
- `requirements.txt`: 필요한 Python 패키지 목록
- `.gitignore`: Git에 올리면 안 되는 파일 목록

## 실행 준비

필요한 패키지를 설치합니다.

```bash
pip install -r requirements.txt
```

`.env` 파일에는 아래 값이 필요합니다.

```env
NOTION_API_KEY=여기에_Notion_API_키
DATABASE_ID=여기에_Notion_과제_관리_DB_ID
PROJECT_DATABASE_ID=여기에_Notion_프로젝트_DB_ID
STUDY_DATABASE_ID=여기에_Notion_공부_기록_DB_ID
```

실제 API 키와 데이터베이스 ID는 외부에 공개하면 안 됩니다.

## 실행 방법

터미널에서 프로젝트 폴더로 이동한 뒤 실행합니다.

```bash
python main.py
```

프로그램이 실행되면 아래 메뉴가 표시됩니다.

```text
1) 과제 추가
2) 프로젝트 추가
3) 공부 기록 추가
4) 마감 임박 과제 조회
5) 종료
```

과제 추가는 `DATABASE_ID`, 프로젝트 추가는 `PROJECT_DATABASE_ID`, 공부 기록 추가는 `STUDY_DATABASE_ID`를 사용합니다.

날짜는 `YYYY-MM-DD` 형식으로 입력해야 하며, 잘못 입력하면 다시 입력합니다.
마감 임박 과제 조회는 오늘부터 3일 이내 마감이고 상태가 `완료`, `제출완료`가 아닌 과제를 보여 줍니다.
