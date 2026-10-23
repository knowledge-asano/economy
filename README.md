# 経済スライド 自動更新版（GitHub Pages用）

入口のファイル名は **index.html** です（inndex.html ではありません）。
この一式は、GitHubでデータを定期収集し、GitHub Pagesで表示するためのものです。
HTMLだけをアップロードすると、定期収集は動きません。

## 最初に行うこと

1. ZIPを展開します。
2. GitHubで新しい公開リポジトリを作ります。名前の例：`economy-slides`。初期ブランチは `main` にします。
3. 展開したフォルダの**中身すべて**をリポジトリの一番上にアップロードします。`index.html` がリポジトリ直下に見える状態にしてください。
4. **`.github/workflows/update-and-publish.yml` も含めて**アップロードします。ZIPそのものをアップロードしても公開できません。
5. リポジトリの **Settings → Pages → Build and deployment → Source** で **GitHub Actions** を選びます。
6. **Actions → Update data and publish slides → Run workflow → Run workflow** を押します。
7. 完了後、**Settings → Pages** に表示されたURLを開きます。

URLの形：`https://ユーザー名.github.io/economy-slides/`

ファイルのアップロードで更新設定が見えない場合は、GitHubの **Add file → Create new file** で
`.github/workflows/update-and-publish.yml` を作り、同名ファイルの中身を貼り付けてください。
Windowsでは「.github」の先頭の点を削除しないでください。

## アップロード後の構成

- `index.html`：水彩スライド・表示と操作・初期データ
- `data/latest.json`：収集済みの最新公表値
- `.github/workflows/update-and-publish.yml`：定期収集・保存・公開の設定
- `scripts/update_data.py`：公式データを収集する処理
- `scripts/check_data.py`：公開前に数値・日付・出典を点検
- `scripts/live.js`：表示処理の編集用ソース（表示用HTMLには組み込み済み）
- `tests/`：収集と保持の検証
- `requirements.txt`：データ収集で利用するライブラリ
- `.nojekyll`、`.gitignore`：公開・保存の設定
- `README.md`：この説明書

`.openai` と `dist` は開発用で、この配布ZIPには含みません。

## 自動更新される範囲

| 対象 | 取得先・定義 |
|---|---|
| ドル円 | FRB/FREDのNY正午値。リアルタイム値ではなく、配信にも時間差があります |
| 米10年国債利回り | FRB/FRED・日次 |
| 日本10年国債利回り | 財務省・当月の国債金利CSV |
| 原油 | EIA/FREDのWTI・ブレント**現物**。先物とは異なります |
| 米国CPI | BLS最新発表の総合・食料及びエネルギー除く、前年同月比 |
| 日本CPI | 総務省最新発表の総合・生鮮食品除く・生鮮食品及びエネルギー除く、前年同月比 |
| 米国政策金利 | FRB/FREDのFF金利誘導目標の上下限 |
| 日本政策金利 | 日銀の最新公表文にある翌日物コールレート誘導目標 |

表示される数字・物価グラフ・原油グラフ・日米長期金利差を連動更新します。
日経平均とS&P500は公式画面へのリンクにしています。FREDの当該系列には第三者への再配信条件があるため、この公開用設定では指数のデータを複製しません。

介入・財政・AI・2026年10月の市場事例は日付を付けて残しています。
新しいニュースの原因分析、制度変更、将来予想まで自動生成する仕組みではありません。
予定は古くならないよう、各機関の公式カレンダーへのリンクにしています。

## 更新のタイミングと操作

- GitHubが毎日 **日本時間6:23頃・17:23頃** に収集・公開します。実行時刻は混雑で遅れる場合があります。
- スライドは開いたときに、公開済みの `data/latest.json` を読み込みます。
- **最新データを確認**：公開済みデータをもう一度読みます。このボタンがGitHubの収集処理を起動するわけではありません。
- すぐ収集したいとき：GitHubの **Actions → Run workflow** を実行します。
- **講義中は固定**：読み込みを止めます。解除すると再確認します。
- **固定版を作成 → 固定HTMLを保存**：その時点のデータを組み込んだ、固定のHTMLをダウンロードします。
- **出典**：指標ごとの対象日・取得日時・出典・保持状態を確認できます。

## 取得できないとき

一部の取得先が失敗した場合、その指標の最後に取得できた値を残し、「前回値を保持」と表示します。
数値が0になったり、架空の最新値になったりすることはありません。初回から未取得の項目は「—」です。
サイトへの接続が失敗したときは、この端末に保存された直近データ、またはHTML内の初期データを表示します。
48時間以上収集を確認できない場合は、その旨を上部に表示します。指標の対象日も別に表示します。

政策金利が変わらない間、政策決定日が古いのは正常です。月次統計と日次相場も同じ日付にはなりません。
配信元のHTMLや金融政策の枠組みが変わると、収集処理の調整が必要になることがあります。

## GitHubでうまく動かないとき

- `Settings → Pages` のSourceが **GitHub Actions** か確認してください。
- Actionsが無効なら **I understand my workflows, go ahead and enable them** 等の有効化ボタンを押します。
- 書き込み権限エラーなら **Settings → Actions → General → Workflow permissions** を確認します。
- ブランチ保護でデータ保存が拒否される場合は、公開専用のリポジトリを使うか、Actionsの書き込みが許可された運用にしてください。
- 初回の公開が始まらなければ **Run workflow** を実行します。
- 公開リポジトリで長期間更新がないと、GitHub側が定期実行を停止する場合があります。Actions画面で再度有効にできます。

## データ利用と出典

FRB/FRED、EIA、財務省、BLS、総務省、日本銀行の公表資料を参照しています。
表示は教育用で、取引に使えるリアルタイム気配値ではありません。
GitHubの標準ワークフロー用トークン以外のAPIキーは、初期設定では不要です。

公式ドキュメント：
- https://docs.github.com/en/pages/getting-started-with-github-pages/creating-a-github-pages-site
- https://docs.github.com/en/pages/getting-started-with-github-pages/using-custom-workflows-with-github-pages
- https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows
- https://fred.stlouisfed.org/series/NIKKEI225
- https://fred.stlouisfed.org/series/SP500

## 作成時の確認

同梱データは公式サイトへの実接続で収集しています。構造・数値保持・グラフ・画面操作を点検し、結果は `QA.md` に記載します。
GitHub上での定期実行・公開は、この一式をアップロードしてPagesを設定した後に始まります。
