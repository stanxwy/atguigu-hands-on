# 下载模型到当前目录下的 models/bge-m3 文件夹
# model_dir = snapshot_download('Xorbits/bge-m3', cache_dir='D:/ai_models/modelscope_cache')
# print(f"模型已下载到: {model_dir}")

from modelscope.hub.snapshot_download import snapshot_download

# 下载模型到当前目录下的 models/bge-m3 文件夹
model_dir = snapshot_download('BAAI/bge-m3', cache_dir='D:/ai_models/modelscope_cache')
print(f"模型已下载到: {model_dir}")

"""
(knowledge-base) PS D:\knowledge-base> python -m app.tool.download_bgem3
2026-07-13 13:00:52,711 | INFO    | modelscope_hub.download | Downloading 30 files from BAAI/bge-m3@master
Downloading:  80%|████████████████████████████████████████████████████████████████████████████████████████████                       | 24/30 [01:00<00:45,  7.62s/file]2026-07-13 13:01:55,974 | WARNING | modelscope_hub.download | Download failed for imgs/nqa.jpg: HTTPSConnectionPool(host='modelscope.cn', port=443): Read timed out., will retrynnx_data:   3%|██▊                                                                                                          | 57.7M/2.27G [00:59<50:58, 722kB/s]
Downloading:  90%|███████████████████████████████████████████████████████████████████████████████████████████████████████▌           | 27/30 [01:21<00:17,  5.76s/file]2026-07-13 13:02:34,647 | WARNING | modelscope_hub.download | Download failed for imgs/nqa.jpg: ('Connection broken: IncompleteRead(63134 bytes read, 95224 more expected)', IncompleteRead(63134 bytes read, 95224 more expected)), will retry                                                            | 95.4M/2.27G [01:38<28:07, 1.29MB/s]
Downloading: 100%|███████████████████████████████████████████████████████████████████████████████████████████████████████████████████| 30/30 [37:22<00:00, 74.75s/file]
模型已下载到: D:\ai_models\modelscope_cache\models\BAAI--bge-m3\snapshots\master                                                                                
"""