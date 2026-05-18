# KBT Daily Dashboard

川崎ブレイブサンダース コンディショニングダッシュボード。

## 機能

- 選手・日付を選択してACWR（急性:慢性ワークロード比）を確認
- LOAD / EXERTION / CHANGE / SPRINT の4指標を表示
- 28日間のACWRトレンドグラフ
- CSVアップロードでデータを追記

## ローカル起動

```bash
pip install -r requirements.txt
streamlit run app.py
```

## データ更新

`data/rawdata.csv` と同じカラム構成のCSVをサイドバーからアップロードすると自動追記されます。

必須カラム: `Date, VS, Name, Accumulated Acceleration Load, Exertions, Changes of Orientation, SPRINT, CATEGORY`
