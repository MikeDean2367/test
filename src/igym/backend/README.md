# LiteLLM
官方文档：
https://docs.litellm.ai/docs/

异常处理：
https://docs.litellm.ai/docs/exception_mapping


Function Calling：
https://docs.litellm.ai/docs/completion/function_call#step-2----parse-the-model-response-and-execute-functions

Route：（供参考）
https://docs.litellm.ai/docs/routing


/disk/disk_20T/zjt/bench/MLBench/scratch_litellm.py

# APIManager:
1. 可以思考一下这里的配置文件格式
(下面是我之前写的一个版本)
···json
{
    "diy_group_1": {
        "class": "LiteLLMBackend",
        "base_url": "https://base.url",
        "api_keys": [
            "key1",
            "key2",
            "key3"
        ],
        "model": [
            "gpt", "llama"
        ],
        "decode": {
            "temperature": 0,
            "top_p": 0.9,
            "max_tokens": 1000
        }
    },
    "diy_group_2": {
        "class": "LiteLLMBackend",
        "base_url": "https://base.url",
        "api_keys": [
            "key4",
            "key5",
            "key6"
        ],
        "model": [
            "claude", "deepseek"
        ]
    },
    "diy_group_3": {
        "class": "LiteLLMBackend",
        "base_url": [
            "https://base.url1",
            "https://base.url2",
            "https://base.url3"
        ],
        "qps": [
            ...
        ],
        "api_keys": [
            "key4",
            "key5",
            "key6"
        ],
        "model": [
            "claude"
        ]
    }
}
```

2. limit，QPS
3. 


