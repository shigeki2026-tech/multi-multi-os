# Local Setup

## 対象

multi-multi-os のローカル起動手順。

## 通常起動

```powershell
cd "$env:USERPROFILE\Documents\Projects\multi-multi-os"
taskkill /F /IM python.exe 2>$null
git pull origin main
streamlit run app.py
```

## SQLite DBについて

`multimulti_os.db` はローカル実体であり、git管理しない。

既存PCでは、現在の `multimulti_os.db` をそのまま使用する。

新規PCでは、以下のどちらかの方式を採用する。

1. アプリ起動時にDBが自動生成される場合
   - `streamlit run app.py` で起動
   - 必要なマスタを画面から登録

2. DB初期化処理が未整備の場合
   - seed SQL または初期化スクリプトを別途作成する
   - DB実体そのものはgitに戻さない

## 注意

DBをgitに戻さないこと。

共有が必要な初期データは、DBファイルではなく seed script / CSV / migration として管理する。
