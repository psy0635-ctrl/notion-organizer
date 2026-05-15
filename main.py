from datetime import date, datetime, timedelta
import logging
import os

from dotenv import load_dotenv
from notion_client import Client


# ============================================================
# Notion 학습 대시보드 자동화 프로그램
# ------------------------------------------------------------
# 이 프로그램은 터미널에서 메뉴를 보여 주고,
# 사용자가 선택한 기능에 따라 Notion 데이터베이스를 다룹니다.
#
# 지원 기능:
# 1) 과제 추가
# 2) 프로젝트 추가
# 3) 공부 기록 추가
# 4) 마감 임박 과제 조회
# 5) 종료
#
# .env 파일에는 아래 환경 변수가 필요합니다.
# - NOTION_API_KEY: Notion 통합 API 키
# - DATABASE_ID: 과제 관리 데이터베이스 ID
# - PROJECT_DATABASE_ID: 프로젝트 데이터베이스 ID
# - STUDY_DATABASE_ID: 공부 기록 데이터베이스 ID
#
# 보안 주의:
# - .env 파일의 실제 값은 절대 print하지 않습니다.
# - 오류가 나도 API 키나 DB ID 값은 화면에 보여 주지 않습니다.
# ============================================================


# Notion 라이브러리가 내부적으로 출력하는 경고 로그를 숨깁니다.
# 사용자가 봐야 할 메시지는 아래 코드에서 직접 한국어로 출력합니다.
logging.getLogger("notion_client").disabled = True


# ============================================================
# 1. 과제 관리 DB 속성 이름
# ------------------------------------------------------------
# 아래 이름은 Notion 과제 관리 DB의 실제 속성 이름과 같아야 합니다.
# Notion에서 속성 이름을 바꿨다면 여기 상수만 수정하면 됩니다.
# ============================================================
ASSIGNMENT_PROPERTY_NAME = "과제명"
ASSIGNMENT_PROPERTY_SUBJECT = "과목"
ASSIGNMENT_PROPERTY_STATUS = "상태"
ASSIGNMENT_PROPERTY_PRIORITY = "중요도"
ASSIGNMENT_PROPERTY_DEADLINE = "마감일"
ASSIGNMENT_PROPERTY_SUBMIT_LINK = "제출 링크"


# ============================================================
# 2. 프로젝트 DB 속성 이름
# ------------------------------------------------------------
# 프로젝트 DB에는 기본적으로 아래 속성이 있다고 가정합니다.
# 실제 DB 속성 이름이 다르면 이 상수만 바꾸세요.
# ============================================================
PROJECT_PROPERTY_NAME = "프로젝트명"
PROJECT_PROPERTY_STATUS = "상태"
PROJECT_PROPERTY_PRIORITY = "중요도"
PROJECT_PROPERTY_DEADLINE = "마감일"


# ============================================================
# 3. 공부 기록 DB 속성 이름
# ------------------------------------------------------------
# 공부 기록 DB에는 기본적으로 아래 속성이 있다고 가정합니다.
# 실제 DB 속성 이름이 다르면 이 상수만 바꾸세요.
# ============================================================
STUDY_PROPERTY_NAME = "공부 내용"
STUDY_PROPERTY_SUBJECT = "과목"
STUDY_PROPERTY_DATE = "날짜"


# ============================================================
# 4. 번호 선택 목록
# ------------------------------------------------------------
# 사용자가 직접 글자를 입력하면 오타가 날 수 있으므로,
# 자주 쓰는 값은 번호로 선택하게 만듭니다.
# ============================================================
SUBJECTS = [
    "융합UI실습",
    "리눅스 프로그래밍",
    "영상인공지능처리",
    "데이터베이스",
    "Java",
    "Python",
]

STATUSES = [
    "시작 전",
    "진행중",
    "검토중",
    "완료",
    "제출완료",
]

PROJECT_STATUSES = [
    "시작 전",
    "진행중",
    "검토중",
    "완료",
]

PRIORITIES = [
    "높음",
    "보통",
    "낮음",
]


# 마감 임박 과제 조회 기준입니다.
# 오늘부터 3일 뒤까지 마감인 과제를 조회합니다.
UPCOMING_DEADLINE_DAYS = 3


def load_config():
    """Notion 연결에 필요한 환경 변수를 .env 파일에서 읽어 옵니다.

    load_dotenv()는 .env 파일의 내용을 환경 변수로 등록합니다.
    os.getenv()는 등록된 환경 변수 값을 읽어 옵니다.

    중요한 점:
    - 실제 API 키와 DB ID 값은 절대 출력하지 않습니다.
    - 값이 없을 때는 어떤 환경 변수가 빠졌는지만 알려 줍니다.
    """

    load_dotenv()

    config = {
        "notion_api_key": os.getenv("NOTION_API_KEY"),
        "assignment_database_id": os.getenv("DATABASE_ID"),
        "project_database_id": os.getenv("PROJECT_DATABASE_ID"),
        "study_database_id": os.getenv("STUDY_DATABASE_ID"),
    }

    missing_messages = []

    if not config["notion_api_key"]:
        missing_messages.append("NOTION_API_KEY가 없습니다.")

    if not config["assignment_database_id"]:
        missing_messages.append("DATABASE_ID가 없습니다. 과제 관리 DB ID를 추가해 주세요.")

    if not config["project_database_id"]:
        missing_messages.append(
            "PROJECT_DATABASE_ID가 없습니다. 프로젝트 DB ID를 추가해 주세요."
        )

    if not config["study_database_id"]:
        missing_messages.append("STUDY_DATABASE_ID가 없습니다. 공부 기록 DB ID를 추가해 주세요.")

    if missing_messages:
        raise ValueError("\n".join(missing_messages))

    return config


def create_notion_client(notion_api_key):
    """Notion API를 호출하기 위한 Client 객체를 만듭니다."""

    return Client(auth=notion_api_key)


def select_option(title, options):
    """목록을 보여 주고 사용자가 번호로 선택한 값을 반환합니다.

    title은 메뉴 위에 보여 줄 안내 문구입니다.
    options는 선택 가능한 문자열 목록입니다.

    잘못된 값을 입력하면 올바른 번호를 입력할 때까지 다시 물어봅니다.
    """

    while True:
        print(f"\n{title}")

        # enumerate(..., start=1)을 사용하면 번호가 1부터 시작합니다.
        for index, option in enumerate(options, start=1):
            print(f"{index}) {option}")

        choice = input("번호 입력: ").strip()

        if not choice.isdigit():
            print("숫자로 입력해 주세요.")
            continue

        choice_number = int(choice)

        if 1 <= choice_number <= len(options):
            return options[choice_number - 1]

        print("목록에 있는 번호를 입력해 주세요.")


def input_required_text(message):
    """비어 있으면 안 되는 문자열을 입력받습니다.

    과제명, 프로젝트명, 공부 내용처럼 꼭 필요한 값에 사용합니다.
    사용자가 Enter만 누르면 다시 입력하도록 합니다.
    """

    while True:
        value = input(message).strip()

        if value:
            return value

        print("빈 값은 입력할 수 없습니다. 다시 입력해 주세요.")


def input_date(message):
    """YYYY-MM-DD 형식의 날짜를 입력받습니다.

    datetime.strptime()을 사용하면 날짜 형식뿐 아니라
    2026-02-30처럼 실제로 존재하지 않는 날짜도 걸러낼 수 있습니다.
    """

    while True:
        value = input(message).strip()

        try:
            datetime.strptime(value, "%Y-%m-%d")
            return value
        except ValueError:
            print("날짜 형식이 잘못되었습니다. YYYY-MM-DD 형식으로 다시 입력하세요.")


def input_optional_url():
    """제출 링크를 입력받습니다.

    제출 링크는 선택 사항입니다.
    사용자가 Enter만 누르면 None을 반환합니다.
    None이면 Notion에 URL 속성을 보내지 않습니다.
    """

    submit_link = input("제출 링크를 입력하세요. 없으면 Enter: ").strip()

    if submit_link == "":
        return None

    return submit_link


def collect_assignment_input():
    """과제 하나에 필요한 정보를 사용자에게 입력받습니다."""

    print("\n=== 과제 추가 ===")

    return {
        "name": input_required_text("과제명을 입력하세요: "),
        "subject": select_option("과목을 선택하세요.", SUBJECTS),
        "status": select_option("상태를 선택하세요.", STATUSES),
        "priority": select_option("중요도를 선택하세요.", PRIORITIES),
        "deadline": input_date("마감일을 입력하세요. 예) 2026-05-16: "),
        "submit_link": input_optional_url(),
    }


def collect_project_input():
    """프로젝트 하나에 필요한 정보를 사용자에게 입력받습니다."""

    print("\n=== 프로젝트 추가 ===")

    return {
        "name": input_required_text("프로젝트명을 입력하세요: "),
        "status": select_option("상태를 선택하세요.", PROJECT_STATUSES),
        "priority": select_option("중요도를 선택하세요.", PRIORITIES),
        "deadline": input_date("마감일을 입력하세요. 예) 2026-05-30: "),
    }


def collect_study_input():
    """공부 기록 하나에 필요한 정보를 사용자에게 입력받습니다."""

    print("\n=== 공부 기록 추가 ===")

    return {
        "name": input_required_text("공부 내용을 입력하세요: "),
        "subject": select_option("과목을 선택하세요.", SUBJECTS),
        "date": input_date("공부한 날짜를 입력하세요. 예) 2026-05-16: "),
    }


def build_assignment_properties(assignment):
    """과제 입력값을 Notion API가 이해하는 properties 형식으로 바꿉니다."""

    properties = {
        ASSIGNMENT_PROPERTY_NAME: {
            "title": [{"text": {"content": assignment["name"]}}],
        },
        ASSIGNMENT_PROPERTY_SUBJECT: {
            "select": {"name": assignment["subject"]},
        },
        ASSIGNMENT_PROPERTY_STATUS: {
            "select": {"name": assignment["status"]},
        },
        ASSIGNMENT_PROPERTY_PRIORITY: {
            "select": {"name": assignment["priority"]},
        },
        ASSIGNMENT_PROPERTY_DEADLINE: {
            "date": {"start": assignment["deadline"]},
        },
    }

    if assignment["submit_link"]:
        properties[ASSIGNMENT_PROPERTY_SUBMIT_LINK] = {
            "url": assignment["submit_link"],
        }

    return properties


def build_project_properties(project):
    """프로젝트 입력값을 Notion API properties 형식으로 바꿉니다."""

    return {
        PROJECT_PROPERTY_NAME: {
            "title": [{"text": {"content": project["name"]}}],
        },
        PROJECT_PROPERTY_STATUS: {
            "select": {"name": project["status"]},
        },
        PROJECT_PROPERTY_PRIORITY: {
            "select": {"name": project["priority"]},
        },
        PROJECT_PROPERTY_DEADLINE: {
            "date": {"start": project["deadline"]},
        },
    }


def build_study_properties(study):
    """공부 기록 입력값을 Notion API properties 형식으로 바꿉니다."""

    return {
        STUDY_PROPERTY_NAME: {
            "title": [{"text": {"content": study["name"]}}],
        },
        STUDY_PROPERTY_SUBJECT: {
            "select": {"name": study["subject"]},
        },
        STUDY_PROPERTY_DATE: {
            "date": {"start": study["date"]},
        },
    }


def create_page(notion, database_id, properties):
    """전달받은 데이터베이스에 새 페이지를 만듭니다."""

    notion.pages.create(
        parent={"database_id": database_id},
        properties=properties,
    )


def add_assignment(notion, assignment_database_id):
    """과제 정보를 입력받고 과제 관리 DB에 추가합니다."""

    assignment = collect_assignment_input()
    properties = build_assignment_properties(assignment)
    create_page(notion, assignment_database_id, properties)
    print("과제가 과제 관리 DB에 추가되었습니다!")


def add_project(notion, project_database_id):
    """프로젝트 정보를 입력받고 프로젝트 DB에 추가합니다."""

    project = collect_project_input()
    properties = build_project_properties(project)
    create_page(notion, project_database_id, properties)
    print("프로젝트가 프로젝트 DB에 추가되었습니다!")


def add_study_record(notion, study_database_id):
    """공부 기록 정보를 입력받고 공부 기록 DB에 추가합니다."""

    study = collect_study_input()
    properties = build_study_properties(study)
    create_page(notion, study_database_id, properties)
    print("공부 기록이 공부 기록 DB에 추가되었습니다!")


def get_plain_text_from_title(title_property):
    """Notion title 속성에서 사람이 읽을 수 있는 글자만 꺼냅니다."""

    title_items = title_property.get("title", [])

    if not title_items:
        return "(제목 없음)"

    return "".join(item.get("plain_text", "") for item in title_items)


def get_select_name(page, property_name):
    """Notion select 속성에서 선택된 이름을 꺼냅니다."""

    property_value = page["properties"].get(property_name, {})
    select_value = property_value.get("select")

    if not select_value:
        return "-"

    return select_value.get("name", "-")


def get_date_start(page, property_name):
    """Notion date 속성에서 시작 날짜를 꺼냅니다."""

    property_value = page["properties"].get(property_name, {})
    date_value = property_value.get("date")

    if not date_value:
        return "-"

    return date_value.get("start", "-")


def query_upcoming_assignments(notion, assignment_database_id):
    """오늘부터 며칠 안에 마감되는 과제를 조회합니다.

    기준:
    - 마감일이 오늘 이상
    - 마감일이 오늘부터 UPCOMING_DEADLINE_DAYS일 이내
    - 상태가 완료 또는 제출완료가 아닌 과제
    """

    today = date.today()
    end_date = today + timedelta(days=UPCOMING_DEADLINE_DAYS)

    response = notion.databases.query(
        database_id=assignment_database_id,
        filter={
            "and": [
                {
                    "property": ASSIGNMENT_PROPERTY_DEADLINE,
                    "date": {"on_or_after": today.isoformat()},
                },
                {
                    "property": ASSIGNMENT_PROPERTY_DEADLINE,
                    "date": {"on_or_before": end_date.isoformat()},
                },
                {
                    "property": ASSIGNMENT_PROPERTY_STATUS,
                    "select": {"does_not_equal": "완료"},
                },
                {
                    "property": ASSIGNMENT_PROPERTY_STATUS,
                    "select": {"does_not_equal": "제출완료"},
                },
            ],
        },
        sorts=[
            {
                "property": ASSIGNMENT_PROPERTY_DEADLINE,
                "direction": "ascending",
            },
        ],
    )

    return response.get("results", [])


def show_upcoming_assignments(notion, assignment_database_id):
    """마감 임박 과제를 조회하고 터미널에 보기 좋게 출력합니다."""

    print(f"\n=== 마감 임박 과제 조회: 오늘부터 {UPCOMING_DEADLINE_DAYS}일 이내 ===")

    assignments = query_upcoming_assignments(notion, assignment_database_id)

    if not assignments:
        print("마감 임박 과제가 없습니다.")
        return

    for index, page in enumerate(assignments, start=1):
        properties = page["properties"]
        name = get_plain_text_from_title(properties.get(ASSIGNMENT_PROPERTY_NAME, {}))
        subject = get_select_name(page, ASSIGNMENT_PROPERTY_SUBJECT)
        status = get_select_name(page, ASSIGNMENT_PROPERTY_STATUS)
        priority = get_select_name(page, ASSIGNMENT_PROPERTY_PRIORITY)
        deadline = get_date_start(page, ASSIGNMENT_PROPERTY_DEADLINE)

        print(f"{index}. [{deadline}] {name}")
        print(f"   과목: {subject} / 상태: {status} / 중요도: {priority}")


def select_main_menu():
    """프로그램 시작 메뉴를 보여 주고 사용자의 선택을 반환합니다."""

    return select_option(
        "원하는 기능을 선택하세요.",
        [
            "과제 추가",
            "프로젝트 추가",
            "공부 기록 추가",
            "마감 임박 과제 조회",
            "종료",
        ],
    )


def print_notion_error(error, action_name):
    """Notion 작업에 실패했을 때 친절한 오류 안내를 출력합니다.

    실제 API 키나 DB ID 값은 출력하지 않습니다.
    """

    print(f"{action_name} 실패")
    print("오류 내용:", error)
    print("확인할 항목: API 키, DB ID, Notion 속성 이름, select 옵션 이름")


def run_program():
    """프로그램 전체 흐름을 담당하는 함수입니다."""

    print("=== Notion 학습 대시보드 자동화 프로그램 ===")

    try:
        config = load_config()
    except ValueError as error:
        print("설정 오류")
        print(error)
        print(".env 파일을 수정한 뒤 다시 실행해 주세요.")
        return

    notion = create_notion_client(config["notion_api_key"])

    while True:
        selected_menu = select_main_menu()

        if selected_menu == "과제 추가":
            try:
                add_assignment(notion, config["assignment_database_id"])
            except Exception as error:
                print_notion_error(error, "과제 추가")

        elif selected_menu == "프로젝트 추가":
            try:
                add_project(notion, config["project_database_id"])
            except Exception as error:
                print_notion_error(error, "프로젝트 추가")

        elif selected_menu == "공부 기록 추가":
            try:
                add_study_record(notion, config["study_database_id"])
            except Exception as error:
                print_notion_error(error, "공부 기록 추가")

        elif selected_menu == "마감 임박 과제 조회":
            try:
                show_upcoming_assignments(notion, config["assignment_database_id"])
            except Exception as error:
                print_notion_error(error, "마감 임박 과제 조회")

        elif selected_menu == "종료":
            print("프로그램을 종료합니다.")
            break


# 이 파일을 직접 실행했을 때만 run_program()을 호출합니다.
# 다른 파일에서 함수를 import할 때 프로그램이 자동 실행되는 것을 막아 줍니다.
if __name__ == "__main__":
    run_program()
