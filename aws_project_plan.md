# AWS個人開発計画

## 目的

AWS経験を作り、面談で「AWS上でWebアプリを構築・運用した経験があります」と言えるようにする。
従来型（EC2/RDS）とサーバーレス（Lambda）の両方をカバーする。

## 前提条件

- AWS Free Tier（12ヶ月無料）を利用
- 9ヶ月目に全リソース削除→アカウント閉鎖で確実に0円
- Billing Alertを$1で設定すること
- 使わない時はEC2/RDSを停止

## 実施順序

1. shift出勤表をRailway + GitHub Actions CI/CDで完成させる
2. 同じshift出勤表をAWS EC2/RDS/S3/DynamoDBにデプロイ（Plan A）
3. ai-writing-assistantのFastAPIバックエンドをAWS Lambda + API Gatewayに移行（Plan B）

---

## Plan A: shift出勤表 → AWS従来型 + DynamoDB

### 使用するAWSサービス

| サービス | 用途 | 無料枠 |
|---------|------|--------|
| EC2 t2.micro | アプリケーションサーバー | 750時間/月（12ヶ月） |
| RDS t2.micro (PostgreSQL) | メインDB（従業員マスタ、出退勤記録） | 750時間/月（12ヶ月） |
| S3 | ファイル保存（CSV出力、バックアップ） | 5GB（12ヶ月） |
| DynamoDB | 操作ログ（打刻履歴、データ変更履歴） | 25GB（永久無料） |

### RDS に入れるデータ（関係型データ）

- 従業員マスタ（社員ID、氏名、部署、権限）
- 出退勤記録（社員ID、日付、出勤時刻、退勤時刻、勤務時間）
- 部署マスタ
- 勤務形態マスタ（正社員、パート等）

### DynamoDB に入れるデータ（操作ログ）

- 打刻ログ（誰が、いつ、どの端末から打刻したか）
- データ修正履歴（誰が、いつ、何を、どう変更したか）
- ログインログ

DynamoDBを選ぶ理由：
- 書き込みが多く、読み込みは少ない（ログの特性に合致）
- スキーマが固定でなくてよい（ログの種類によって項目が異なる）
- 大量データでもコストが低い
- 面談で「RDSとDynamoDBを用途に応じて使い分けた」と説明できる

### 構成図

```
ブラウザ
  │
  ▼
EC2 (アプリサーバー)
  ├── RDS (PostgreSQL) ← 従業員・出退勤データ
  ├── DynamoDB          ← 操作ログ・変更履歴
  └── S3               ← CSV出力・バックアップ
```

### Railway版との違い（面談で語れるポイント）

- Railway版：PaaS、設定不要で即デプロイ
- AWS版：VPC、Security Group、IAMロールを自分で設定
- 同じアプリを異なるインフラに載せた経験 → クラウド移行の知見

---

## Plan B: ai-writing-assistant → AWSサーバーレス

### 使用するAWSサービス

| サービス | 用途 | 無料枠 |
|---------|------|--------|
| Lambda | 3つのAPIエンドポイント | 月100万リクエスト（永久無料） |
| API Gateway | HTTPリクエストのルーティング | 月100万コール（12ヶ月） |

### Lambda関数の構成

| 関数名 | 元のFastAPIエンドポイント | 処理内容 |
|--------|--------------------------|---------|
| translate | POST /api/ai/translate | Claude APIで翻訳 |
| summarize | POST /api/ai/summarize | Claude APIで要約 |
| generate | POST /api/ai/generate | Claude APIで文章生成 |

### 構成図

```
ブラウザ (Next.js on Vercel)
  │
  ▼
API Gateway
  ├── /translate  → Lambda (translate)  → Claude API
  ├── /summarize  → Lambda (summarize)  → Claude API
  └── /generate   → Lambda (generate)   → Claude API
```

### データベースは不要

- このアプリは入力→AI処理→出力の完結型
- DBを無理に追加しない（不自然になるため）
- Lambda + API Gatewayの純粋なサーバーレスAPI移行として見せる

### Vercel版との違い（面談で語れるポイント）

- Vercel版：Next.js API Routesでバックエンド代替
- AWS版：Lambda + API Gatewayで独立したサーバーレスAPI
- FastAPI → Lambda への移行パターンを経験

---

## 面談での説明イメージ

### Plan A（従来型）

> 勤怠管理システムをAWS上で構築しました。
> アプリケーションサーバーはEC2、データベースはRDS（PostgreSQL）で従業員・出退勤データを管理し、
> 操作ログはDynamoDBに記録しています。
> RDSとDynamoDBはデータの特性に応じて使い分けており、
> CSVエクスポートやバックアップにはS3を利用しています。
> VPC、Security Group、IAMロールの設定も自分で行いました。

### Plan B（サーバーレス）

> AI文章作成ツールのバックエンドをFastAPIからAWS Lambdaに移行しました。
> 翻訳・要約・文章生成の3つのAPIをそれぞれ独立したLambda関数として実装し、
> API Gatewayでルーティングしています。
> サーバー管理が不要になり、リクエスト単位の課金で運用コストも最小限です。

---

## 無料枠の注意事項

- EC2/RDS: 12ヶ月無料 → 9ヶ月目に削除予定
- Lambda/DynamoDB: 永久無料 → 削除不要（放置でも課金されない）
- S3: 12ヶ月無料 → 9ヶ月目に削除
- Billing Alert: アカウント作成直後に$1で設定
- クレジットカード登録必須

## CI/CD（GitHub Actions）

shift出勤表のRailway版で構築したGitHub Actions CI/CDパイプラインを、
AWS版でも同様に設定する。

```
push → lint → test → build → deploy (AWS)
```

これにより「GitHub ActionsでCI/CDパイプラインを構築し、AWS環境への自動デプロイを実現」と言える。
