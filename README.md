# LLMs-Conversation

Generate a conversation between two LLMs based on a given scenario. 给定一个场景，让两个大模型以各自的角色进行对话。

![demo](demo.png)

## 设置

目前支持 Openai 兼容的 API 方式调用 LLM 模型，需要将 API 的地址和模型名称设置在 `llmconversation.py` 的 llm_model 中，比如：

```python
llm_model = {
    "deepseek-r1:32b": {
        "model": "deepseek-r1:32b",
        "url": "http://localhost:11434/v1",
        "key": "ollama"
    },
    "qwen2.5:32b": {
        "model": "qwen2.5:32b",
        "url": "http://localhost:11434/v1",
        "key": "ollama"
    },
    "Gemini1.5-flash": {
        "model": "Gemini 1.5 Flash",
        "url": "https://generativelanguage.googleapis.com",
        "key": "YOUR_KEY_HERE"
    }
}
```

## 运行

直接运行 llmconversation.py：

```bash
python llmconversation.py
```

然后在浏览器中访问 `http://127.0.0.1:5000` ，输入角色名称和场景描述，点击 “Start” 就开始对话。点击 “Stop” 可以停止对话。也可以在场景中给出「想结束对话，则在对话最后输出\<end> 标记」类似的提示，这样程序在检测到两个模型都输出了\<end>标记后就会自动结束对话。
