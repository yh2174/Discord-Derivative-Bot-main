# Discord Bot

이 디스코드 봇은 다양한 기능을 제공합니다:
- **노래**: Discord 서버에서 음악을 재생할 수 있습니다.
- **TTS (Text-to-Speech)**: 텍스트를 음성으로 변환하여 읽어줍니다.
- **투표**: 서버에서 투표를 생성하고 관리할 수 있습니다.
- **끝말잇기**: 끝말잇기 게임을 즐길 수 있습니다.
- **낚시**: 가상의 낚시 게임을 통해 재미를 더합니다.
- **권한 설정**: 봇의 권한을 쉽게 설정할 수 있습니다.
- **로그**: 다양한 이벤트와 활동을 기록합니다.

## 설치 및 설정

**python 3.11 이상의 버전을 요구합니다.**

이 봇을 사용하기 위해서는 다음과 같은 설정이 필요합니다.

### 1. `cookies.txt` 파일 작성

1. [GET cookies 브라우저 확장 프로그램](https://chrome.google.com/webstore/detail/get-cookies/kpniiljlnkjmfjpbapecfclcfhpoocmk) 을 사용하여 `cookies.txt` 파일을 작성합니다.
2. 해당 파일은 봇의 노래 기능이 작동하는 데 필요합니다.

### 2. `config.ini` 파일 설정

1. 프로젝트 루트 디렉토리에 `config.ini` 파일을 생성합니다.
2. 다음과 같은 내용을 추가하여 봇 토큰과 어플리케이션 ID를 설정합니다.

    ```ini
    [DEFAULT]
    TOKEN = your_discord_bot_token_here
    APPLICATION_ID = your_discord_application_id_here
    ```

## 사용 방법
### Windows
- start.bat을 실행시킵니다.
### Linux/UNIX
1. 필요한 패키지를 설치합니다.
    ```bash
    pip install -r requirements.txt
    ```
2. 봇을 실행합니다.
    ```bash
    python bot.py
    ```
