
# GDSC KU Discord Bot

이 프로젝트는 **GDSC KU**의 **디스코드 봇**입니다. 이 봇은 **Notion API**와 **Discord API**를 사용하여 GDSC KU 팀의 일정 및 멤버 관리를 효율적으로 돕습니다. Discord 채널에서 명령어를 입력하면 Notion 데이터베이스에서 정보를 가져오거나 업데이트할 수 있습니다.


## 명령어 목록

- **!내정보**  
  사용자의 정보를 Notion에서 검색하여 DM으로 전송합니다.

- **!일정**  
  일정 데이터베이스에서 특정 조건으로 일정을 검색하고 결과를 표시합니다. 조건으로 `name`, `date`, `tag` 등을 사용할 수 있습니다.

- **!멤버**  
  Notion에서 특정 이름 또는 Discord ID로 멤버를 검색합니다.

- **!공지생성**  
  Notion 일정 페이지를 기반으로 출석 또는 등록 공지를 작성합니다. 출석 공지를 작성하면 지정된 시간 후 출석 여부가 자동으로 확인되며, 생성자에게 결과가 DM으로 전달됩니다.


## 설치 및 실행 방법
### No Docker 🥹😴

1. **사전 준비**:
   - Notion API와 Discord API의 API 키를 준비합니다.
   - 루트 디렉토리에 `.env` 파일을 생성하고, 다음과 같이 **DISCORD_TOKEN**과 **NOTION_API_KEY** 값을 설정합니다:

     ```bash
     DISCORD_TOKEN=<Your Discord Bot Token>
     NOTION_API_KEY=<Your Notion API Key>
     NOTION_MEMBER_DB_ID=<Your Notion Member Database ID>
     NOTION_SCHEDULE_DB_ID=<Your Notion Schedule Database ID>
     ```

2. **의존성 설치**:
   ```bash
   pip install -r requirements.txt
   ```

3. **봇 실행**:
   ```bash
   python bot.py
   ```


### Yes Docker 🥰🤩🐋


**1. 준비 사항**

- **Docker** 및 **Docker Compose**가 설치되어 있어야 합니다.
- **`.env` 파일**이 필요합니다.
   ```env
      DISCORD_TOKEN=your_discord_token_here
      NOTION_API_KEY=your_notion_api_key_here
      NOTION_MEMBER_DB_ID=your_member_db_id_here
      NOTION_SCHEDULE_DB_ID=your_schedule_db_id_here
   ```


**2. Docker 사용 명령어**
1. Docker Hub에서 이미지 가져오기

```bash
git clone https://github.com/JeonSeongHu/discord-bot-test.git
cd discord-bot-test
docker pull jsh0423/discord-bot
```

2) Docker Compose로 실행

>   `/path/to/your/project/.env`을 실제 파일 경로로 수정해주세요.
```bash'
# Docker Compose로 봇 실행
docker-compose --env-file /path/to/your/project/.env up
```




## 상세 기능

### 1. **내정보 명령어 (`!내정보`)**  
   - 사용자의 Discord ID를 기반으로 Notion 데이터베이스에서 해당 사용자의 정보를 가져와 사용자에게 DM으로 전송합니다.


**사용 예시**:

```
> !내정보
> 당신의 정보
   노션 ID: ####
   이름: 홍길동
   전공: 정보대학 컴퓨터학과
   학번: 2022320000
   Discord ID: ###
   이메일: ###@gmail.com
   ...
```


### 2. **일정 검색 명령어 (`!일정`)**  
   - 일정과 관련된 정보를 검색하고, 검색된 일정을 사용자에게 보여줍니다. `name`, `date`, `tag` 등의 조건을 사용하여 일정을 검색할 수 있습니다.
   - **`date`는 `부등호`와 `날짜`의 조합으로 검색 가능합니다.** 아래와 같은 규칙이 있습니다. 
      - 등호 (`=`)는 생략 가능합니다.
      - 날짜는 `24-09-03'과 같이 **년-월-일을 모두 표기**해야 합니다.
      - 날짜는 자연어를 일부 지원하며, **`today`, `yesterday` `last/this/next week/month`가 사용 가능**합니다.
   ```
   # 9월 9일에 진행된 모든 branch를 검색
   !일정 name:branch date:24-09-09

   # 오늘 이전의 모든 ai fetch를 검색
   !일정 name:fetch/ai date: <today 

   # 다음 주 진행되는 모든 fetch를 검색
   !일정 name:fetch date: next week

   # 이번 달 이전 진행된 모든 일정을 검색
   !일정 date: <next month
   ```

   **사용 예시**:
   - 여러개의 일정이 검색할 경우, 하나를 골라 선택할 수 있습니다.
   ```
   > !일정 name:branch/git

   > 검색 결과 / 자세히 볼 일정의 번호를 선택해주세요.
      최대 25개까지 표시됩니다:

      1. branch/git/day-1
      장소: 하나과학관 102호
      날짜: 2024-09-09

      2. branch/git/day-2
      장소: 우정정보관 205호
      날짜: 2024-09-12

      3. branch/git
      장소: N/A
      날짜: N/A

   > 1
   
   > 선택된 정보
      노션 ID: ###
      이름: branch/git/day-1
      날짜: 2024-09-09
      장소: 하나과학관 102호

      출석/등록을 받기 위해서는 아래의 명령어를 실행하세요:
      !공지생성 ### 출석
      !공지생성 ### 등록
   ```

### 3. **멤버 검색 명령어 (`!멤버`)**  
   이름 또는 Discord ID를 기반으로 Notion 데이터베이스에서 멤버를 검색합니다.

   **사용 예시**
   - 여러개의 일정이 검색할 경우, 하나를 골라 선택할 수 있습니다.

   ```
   > !멤버 김

   > 검색 결과 / 자세히 볼 멤버의 번호를 선택해주세요.
      최대 25개까지 표시됩니다.:
      1. 김AA
      분야: 💝 DevRel (Developer Relations)
      2. 김BB
      분야: 🖥️ SWE (Software Engineer)
      3. 김CC
      분야: 🖥️ SWE (Software Engineer)
      4. 김DD
      분야: 🖥️ SWE (Software Engineer)

   > 1

   > 선택된 정보
      노션 ID: ####
      이름: 김AA
      전공: 정보대학 컴퓨터학과
      학번: 2022320000
      Discord ID: ###
      이메일: ###@gmail.com
   ...

   ```


### 4. **공지 생성 명령어 (`!공지생성`)**  
   Notion에 저장된 일정에 대한 출석 또는 등록 공지를 작성하고, 공지를 통해 출석 여부를 확인합니다. 출석 공지를 생성한 경우, 5분 후에 출석 여부를 자동으로 확인하여 출석하지 않은 등록자를 `결석자` 목록에 추가하고, 생성자에게 DM으로 출석 결과를 전송합니다.

#### 등록 사용 예시:
- ✅ 이모지를 선택한 모든 멤버들의 정보를 [노션 페이지 ID]의 관계형 속성 `참여자`에 넣습니다.
- 해당 메시지는 삭제되지 않습니다. 
   ```
   > !공지생성 [노션 페이지 ID] 등록

   > 🌳 branch/git/day-1 등록 공지
      이 메시지에 체크하여 🌳 branch/git/day-1에 등록해주세요!
      이름: branch/git/day-1
      날짜: 2024-09-09
      장소: 하나과학관 102호
      ✅ : 1
   ```

#### 출석 사용 예시:
- ✅ 이모지를 선택한 모든 멤버들의 정보를 [노션 페이지 ID]의 관계형 속성 `출석자`에 넣습니다.
- 해당 메시지는 5분 이후 기능을 멈추고, 시간이 종료된 이후에는 `등록자`와 `출석자`를 비교하여 `결석자` 명단을 생성합니다.
- 해당 공지를 생성한 관리자에게는 출석부가 자동으로 발송됩니다.
- (To Do) 결석자에게는 자동으로 결석 사실이 DM으로 알려지며, 소명의 기회가 부여됩니다.

**채널**
   ```
   > !공지생성 [노션 페이지 ID] 등록

   > 🚀 fetch/fe/week-1 출석 공지
      이 메시지에 체크하여 🚀 fetch/fe/week-1에 출석해주세요!
      이름: fetch/fe/week-1
      날짜: 2024-09-11
      장소: 하나과학관 101호
      생성 5분 후에는 체크해도 출석으로 등록되지 않습니다.
   ```

**DM (출석자)**
```
>등록 완료
 branch/git/day-1의 '출석자 (인정 결석 포함)'에 '홍길동'가 추가되었습니다.
```

**DM (관리자)**
```
>출석 확인 결과
   📋 출석자 명단
   홍길동

   📝 등록자 명단
   홍길동, 유재석, 강호동

   ❌ 결석자 명단
   유재석, 강호동
```

## 저작권

© 2024 GDSC KU. All rights reserved.


## 주의사항

- Discord 봇을 정상적으로 실행하려면 **메시지 관리**, **DM 전송** 등의 Discord 권한이 부여되어 있어야 합니다.
- Notion API의 권한을 설정하여, 데이터베이스에 적절한 접근이 가능하도록 설정해야 합니다.

---

이 문서는 GDSC KU에서 제공하는 **GDSC KU Discord Bot**에 대한 사용 설명서입니다.
