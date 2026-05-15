from datetime import date, datetime
import logging
import os

from dotenv import load_dotenv
from notion_client import Client


# ============================================================
# Notion 과제/오늘 할 일 자동화 프로그램
# ------------------------------------------------------------
# 이 프로그램은 터미널에서 메뉴를 보여 준 뒤,
# 사용자가 선택한 기능에 따라 Notion 데이터베이스에 항목을 추가합니다.
#
# 1) 과제 추가:
#    기존 과제 관리 데이터베이스(DATABASE_ID)에 과제를 추가합니다.
#
# 2) 오늘 할 일 추가:
#    오늘 할 일 데이터베이스(TODO_DATABASE_ID)에 할 일을 추가합니다.
#
# 프로그램이 동작하려면 같은 폴더의 .env 파일에 아래 값이 필요합니다.
# - NOTION_API_KEY: Notion 통합에서 발급받은 API 키
# - DATABASE_ID: 과제를 추가할 Notion 과제 관리 DB ID
# - TODO_DATABASE_ID: 오늘 할 일을 추가할 Notion 오늘 할 일 DB ID
#
# 보안 주의:
# - .env 파일에는 중요한 토큰이 들어 있으므로 절대 화면에 출력하지 않습니다.
# - 이 코드도 실제 토큰 값이나 데이터베이스 ID 값을 print하지 않습니다.
# ============================================================


# Notion 클라이언트가 내부적으로 출력하는 경고 로그를 숨깁니다.
# 사용자가 봐야 할 오류는 try/except에서 직접 한국어로 안내합니다.
logging.getLogger("notion_client").disabled = True


# ============================================================
# 1. Notion 과제 관리 DB 속성 이름
# ------------------------------------------------------------
# 아래 이름은 Notion 과제 관리 데이터베이스의 속성 이름과 같아야 합니다.
# Notion에서 속성 이름을 바꿨다면 이 상수도 같이 바꾸면 됩니다.
# ============================================================
ASSIGNMENT_PROPERTY_NAME = "과제명"
ASSIGNMENT_PROPERTY_SUBJECT = "과목"
ASSIGNMENT_PROPERTY_STATUS = "상태"
ASSIGNMENT_PROPERTY_PRIORITY = "중요도"
ASSIGNMENT_PROPERTY_DEADLINE = "마감일"
ASSIGNMENT_PROPERTY_SUBMIT_LINK = "제출 링크"


# ============================================================
# 2. Notion 오늘 할 일 DB 속성 이름
# ------------------------------------------------------------
# 오늘 할 일 DB에 아래 속성이 있어야 합니다.
# 만약 실제 DB 속성 이름이 다르다면 이 부분만 수정하세요.
#
# 예:
# - 할 일 대신 이름이라는 제목 속성을 쓴다면 TODO_PROPERTY_NAME = "이름"
# - 날짜 대신 오늘이라는 날짜 속성을 쓴다면 TODO_PROPERTY_DATE = "오늘"
# ============================================================
TODO_PROPERTY_NAME = "할 일"
TODO_PROPERTY_STATUS = "상태"
TODO_PROPERTY_PRIORITY = "중요도"
TODO_PROPERTY_DATE = "날짜"


# ============================================================
# 3. 번호 선택 목록
# ------------------------------------------------------------
# 과목, 상태, 중요도는 사용자가 직접 글자를 입력하지 않고
# 번호로 선택하도록 목록으로 관리합니다.
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

PRIORITIES = [
    "높음",
    "보통",
    "낮음",
]


def load_config():
    """Notion 연결에 필요한 환경 변수를 .env 파일에서 읽어 옵니다.

    load_dotenv()는 .env 파일의 내용을 환경 변수로 등록합니다.
    os.getenv()는 등록된 환경 변수 값을 읽어 옵니다.

    중요한 점:
    - 실제 API 키와 DB ID 값은 절대 출력하지 않습니다.
    - 값이 없는 경우에만 어떤 항목이 빠졌는지 알려 줍니다.
    """

    load_dotenv()

    notion_api_key = os.getenv("NOTION_API_KEY")
    assignment_database_id = os.getenv("DATABASE_ID")
    todo_database_id = os.getenv("TODO_DATABASE_ID")

    if not notion_api_key:
        raise ValueError(".env 파일에 NOTION_API_KEY가 없습니다.")

    if not assignment_database_id:
        raise ValueError(".env 파일에 DATABASE_ID가 없습니다.")

    # TODO_DATABASE_ID는 프로그램 시작 시 바로 검사합니다.
    # 사용자가 2번 메뉴를 눌렀을 때 뒤늦게 실패하는 것보다,
    # 시작할 때 필요한 설정이 빠졌다고 알려 주는 편이 이해하기 쉽습니다.
    if not todo_database_id:
        raise ValueError(
            ".env 파일에 TODO_DATABASE_ID가 없습니다. "
            "오늘 할 일 DB ID를 TODO_DATABASE_ID=... 형식으로 추가해 주세요."
        )

    return notion_api_key, assignment_database_id, todo_database_id


def create_notion_client(notion_api_key):
    """Notion API를 호출하기 위한 Client 객체를 만듭니다."""

    return Client(auth=notion_api_key)


def select_option(title, options):
    """목록을 보여 주고 사용자가 번호로 선택한 값을 반환합니다.

    title은 메뉴 위에 보여 줄 안내 문구입니다.
    options는 선택 가능한 문자열 목록입니다.

    예를 들어 options가 ["높음", "보통", "낮음"]이면
    사용자는 1, 2, 3 중 하나를 입력합니다.
    잘못 입력하면 올바른 번호를 입력할 때까지 다시 물어봅니다.
    """

    while True:
        print(f"\n{title}")

        # enumerate(..., start=1)을 사용하면 번호가 1부터 시작합니다.
        for index, option in enumerate(options, start=1):
            print(f"{index}. {option}")

        choice = input("번호 입력: ").strip()

        # 숫자가 아닌 값을 int()로 바꾸면 오류가 나므로 먼저 검사합니다.
        if not choice.isdigit():
            print("숫자로 입력해 주세요.")
            continue

        choice_number = int(choice)

        # 사용자가 고른 번호가 목록 범위 안에 있는지 확인합니다.
        if 1 <= choice_number <= len(options):
            return options[choice_number - 1]

        print("잘못 입력했습니다. 목록에 있는 번호를 다시 입력하세요.")


def input_required_text(message):
    """반드시 필요한 문자열을 입력받습니다.

    과제명이나 할 일 제목처럼 꼭 필요한 값은 빈 문자열이면 안 됩니다.
    사용자가 Enter만 누르면 다시 입력하도록 합니다.
    """

    while True:
        value = input(message).strip()

        if value:
            return value

        print("빈 값은 입력할 수 없습니다. 다시 입력해 주세요.")


def input_deadline():
    """마감일을 YYYY-MM-DD 형식으로 입력받습니다.

    datetime.strptime()은 문자열이 지정한 날짜 형식과 맞는지 검사합니다.
    2026-02-30처럼 실제로 존재하지 않는 날짜도 잘못된 입력으로 처리됩니다.
    """

    while True:
        deadline = input("마감일을 입력하세요. 예) 2026-05-16: ").strip()

        try:
            datetime.strptime(deadline, "%Y-%m-%d")
            return deadline
        except ValueError:
            print("날짜 형식이 잘못되었습니다. YYYY-MM-DD 형식으로 다시 입력하세요.")


def input_optional_url():
    """제출 링크를 입력받습니다.

    제출 링크는 선택 사항입니다.
    사용자가 Enter만 누르면 None을 반환하고,
    이 경우 Notion에 URL 속성을 보내지 않습니다.
    """

    submit_link = input("제출 링크를 입력하세요. 없으면 Enter: ").strip()

    if submit_link == "":
        return None

    return submit_link


def collect_assignment_input():
    """과제 하나에 필요한 정보를 사용자에게 입력받습니다.

    이 함수는 Notion API를 호출하지 않습니다.
    입력값을 모아서 딕셔너리로 정리하는 역할만 합니다.
    """

    print("\n=== 새 과제 추가 ===")

    return {
        "name": input_required_text("과제명을 입력하세요: "),
        "subject": select_option("과목을 선택하세요.", SUBJECTS),
        "status": select_option("상태를 선택하세요.", STATUSES),
        "priority": select_option("중요도를 선택하세요.", PRIORITIES),
        "deadline": input_deadline(),
        "submit_link": input_optional_url(),
    }


def collect_todo_input():
    """오늘 할 일 하나에 필요한 정보를 사용자에게 입력받습니다.

    오늘 할 일은 오늘 날짜가 자동으로 들어갑니다.
    상태와 중요도는 과제 추가와 같은 번호 선택 방식을 사용합니다.
    """

    print("\n=== 오늘 할 일 추가 ===")

    return {
        "name": input_required_text("할 일을 입력하세요: "),
        "status": select_option("상태를 선택하세요.", STATUSES),
        "priority": select_option("중요도를 선택하세요.", PRIORITIES),
        "date": date.today().isoformat(),
    }


def build_assignment_properties(assignment):
    """과제 입력값을 Notion API의 properties 형식으로 바꿉니다."""

    properties = {
        ASSIGNMENT_PROPERTY_NAME: {
            "title": [
                {
                    "text": {
                        "content": assignment["name"],
                    },
                },
            ],
        },
        ASSIGNMENT_PROPERTY_SUBJECT: {
            "select": {
                "name": assignment["subject"],
            },
        },
        ASSIGNMENT_PROPERTY_STATUS: {
            "select": {
                "name": assignment["status"],
            },
        },
        ASSIGNMENT_PROPERTY_PRIORITY: {
            "select": {
                "name": assignment["priority"],
            },
        },
        ASSIGNMENT_PROPERTY_DEADLINE: {
            "date": {
                "start": assignment["deadline"],
            },
        },
    }

    # 제출 링크가 있을 때만 URL 속성을 추가합니다.
    # 빈 URL을 보내면 Notion API에서 오류가 날 수 있습니다.
    if assignment["submit_link"]:
        properties[ASSIGNMENT_PROPERTY_SUBMIT_LINK] = {
            "url": assignment["submit_link"],
        }

    return properties


def build_todo_properties(todo):
    """오늘 할 일 입력값을 Notion API의 properties 형식으로 바꿉니다.

    오늘 할 일 DB에는 기본적으로 아래 속성이 있다고 가정합니다.
    - 할 일: title
    - 상태: select
    - 중요도: select
    - 날짜: date
    """

    return {
        TODO_PROPERTY_NAME: {
            "title": [
                {
                    "text": {
                        "content": todo["name"],
                    },
                },
            ],
        },
        TODO_PROPERTY_STATUS: {
            "select": {
                "name": todo["status"],
            },
        },
        TODO_PROPERTY_PRIORITY: {
            "select": {
                "name": todo["priority"],
            },
        },
        TODO_PROPERTY_DATE: {
            "date": {
                "start": todo["date"],
            },
        },
    }


def create_page(notion, database_id, properties):
    """전달받은 Notion 데이터베이스에 새 페이지를 만듭니다.

    과제 추가와 오늘 할 일 추가 모두 결국 Notion 페이지를 만드는 일이므로
    공통 함수로 분리했습니다.
    """

    notion.pages.create(
        parent={"database_id": database_id},
        properties=properties,
    )


def add_assignment(notion, assignment_database_id):
    """과제 정보를 입력받고 과제 관리 DB에 추가합니다."""

    assignment = collect_assignment_input()
    properties = build_assignment_properties(assignment)
    create_page(notion, assignment_database_id, properties)
    print("과제가 Notion 과제 관리 DB에 추가되었습니다!")


def add_todo(notion, todo_database_id):
    """오늘 할 일 정보를 입력받고 오늘 할 일 DB에 추가합니다."""

    todo = collect_todo_input()
    properties = build_todo_properties(todo)
    create_page(notion, todo_database_id, properties)
    print("오늘 할 일이 Notion 오늘 할 일 DB에 추가되었습니다!")


def select_main_menu():
    """프로그램 시작 메뉴를 보여 주고 사용자의 선택을 반환합니다."""

    return select_option(
        "원하는 기능을 선택하세요.",
        ["과제 추가", "오늘 할 일 추가", "종료"],
    )


def print_notion_error(error, target_name):
    """Notion 추가 작업에 실패했을 때 친절한 오류 안내를 출력합니다.

    error 안에 API 키 관련 메시지가 들어 있을 수 있지만,
    실제 토큰 값이나 DB ID 값은 출력하지 않습니다.
    """

    print(f"{target_name} 추가 실패")
    print("오류 내용:", error)
    print("확인할 항목: API 키, DB ID, Notion 속성 이름, select 옵션 이름")


def run_program():
    """프로그램 전체 흐름을 담당하는 함수입니다."""

    print("=== Notion 과제/오늘 할 일 자동화 프로그램 ===")

    try:
        notion_api_key, assignment_database_id, todo_database_id = load_config()
    except ValueError as error:
        print("설정 오류")
        print(error)
        print(".env 파일을 수정한 뒤 다시 실행해 주세요.")
        return

    notion = create_notion_client(notion_api_key)

    while True:
        selected_menu = select_main_menu()

        if selected_menu == "과제 추가":
            try:
                add_assignment(notion, assignment_database_id)
            except Exception as error:
                print_notion_error(error, "과제")

        elif selected_menu == "오늘 할 일 추가":
            try:
                add_todo(notion, todo_database_id)
            except Exception as error:
                print_notion_error(error, "오늘 할 일")

        elif selected_menu == "종료":
            print("프로그램을 종료합니다.")
            break


# 이 파일을 직접 실행했을 때만 run_program()을 호출합니다.
# 나중에 다른 파일에서 함수를 import해도 프로그램이 바로 실행되지 않게 하기 위한 코드입니다.
if __name__ == "__main__":
    run_program()
