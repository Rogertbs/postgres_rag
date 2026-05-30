curl http://172.16.200.20:11434/api/generate -d '{
  "model": "qwen2.5:1.5b",
  "prompt": "Por que o céu é azul?",
  "stream": false
}'