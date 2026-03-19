# MultiMulti OS MVP

マルチ業務部向けの業務OS MVPです。

## 今回の整備内容

- UI文言を日本語に整理
- Calendar Phase 1.5 の説明を日本語で整理
- ZIP成果物から `_zip_check` と ZIP ファイル自身を除外して再作成
- 日報送信機能を Gmail 送信対応で本実装
- Gmail送信失敗時の `failed` 履歴保存と画面エラー表示を追加
- `session_state` には ORM オブジェクトを保存せず、ログインユーザーは dict で保持

## Calendar Phase 1.5

Google Calendar は予定の正本として参照します。

- `MockCalendarService`
  Google Calendar API が無効、または設定不足のときに使用します。
- `GoogleCalendarService`
  Google Calendar API の設定が揃っているときに使用します。
- API未設定時はモック予定へ自動フォールバックします。
- API取得失敗時もアプリ全体は停止せず、警告表示のみ行います。

### Calendar 設定

`.env` または環境変数で設定できます。

```dotenv
GOOGLE_CALENDAR_ENABLED=false
GOOGLE_CALENDAR_ID=primary
GOOGLE_SERVICE_ACCOUNT_FILE=C:\path\to\service-account.json
TIMEZONE=Asia/Tokyo
```

## 日報送信機能

日報送信は Gmail SMTP を利用します。

### 実装済み

- 日報テンプレート生成
- 送信前プレビュー
- Gmail送信
- `report_jobs` への送信履歴保存
- Gmail未設定時のドラフト保存
- 送信失敗時の `failed` 保存
- 宛先バリデーション

### Gmail 設定

```dotenv
GMAIL_ENABLED=false
GMAIL_SMTP_HOST=smtp.gmail.com
GMAIL_SMTP_PORT=587
GMAIL_FROM_ADDRESS=your-address@gmail.com
GMAIL_APP_PASSWORD=your-app-password
REPORT_DEFAULT_TO=team@example.com
```

PowerShell 例:

```powershell
$env:GMAIL_ENABLED = "true"
$env:GMAIL_FROM_ADDRESS = "your-address@gmail.com"
$env:GMAIL_APP_PASSWORD = "your-app-password"
$env:REPORT_DEFAULT_TO = "team@example.com"
```

## 起動方法

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
streamlit run app.py
```

## 追加済み依存関係

- `google-api-python-client`
- `google-auth`

## 動作

### Calendar

- API無効または設定不足:
  モック予定を表示します。
- API設定済み:
  Google Calendar の予定を表示します。
- API失敗:
  カレンダー画面は警告表示、ダッシュボードは「取得失敗」を表示します。

### 日報送信

- `sent`
  Gmail SMTP で送信成功した状態です。履歴に `sent` で保存されます。
- `draft`
  Gmail 設定不足などで送信せず、プレビュー本文だけ履歴保存した状態です。
- `failed`
  宛先不正、SMTP接続失敗、認証失敗、送信失敗などで送信できなかった状態です。`preview_text` は保存し、エラー内容は `payload_json.error_message` に保存します。

### Gmail送信失敗時の扱い

- SMTP接続失敗、認証失敗、送信失敗を捕捉します。
- 画面は落とさず `st.error` で表示します。
- `report_jobs` に `failed` で履歴を残します。
- 監査ログも通常どおり記録します。

## 今回まだ未実装

- Google SSO
- Calendar の予定作成、更新、削除
- 複数カレンダー切替
- Teams 連携
- 日報テンプレートの複数種別化
- 添付ファイル送信
