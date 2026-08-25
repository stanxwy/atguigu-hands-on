from modelscope.hub.snapshot_download import snapshot_download

model_dir = snapshot_download('BAAI/bge-reranker-large', cache_dir='D:/ai_models/modelscope_cache')
print(f"模型已下载到: {model_dir}")

"""
2026-07-20 10:11:40,356 | INFO    | modelscope_hub.download | Downloading 12 files from BAAI/bge-reranker-large@master
Downloading: 100%|████████████████████████████████████████████████████████████████████████████████████████████████| 12/12 [36:39<00:00, 183.28s/file]
模型已下载到: D:\ai_models\modelscope_cache\models\BAAI--bge-reranker-large\snapshots\master   
"""