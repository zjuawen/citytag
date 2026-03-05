# CityTag API 请求体生成工具

这个工具用于生成 CityTag API `/api/interface/v2/device3/{uid}` 接口的请求体。

## 安装依赖

```bash
pip install -r requirements.txt
```

或者直接安装：

```bash
pip install pycryptodome
```

## 使用方法

### 方法 1: 直接运行脚本（交互式）

```bash
python3 generate_request_body.py
```

然后按照提示输入相应的信息。

### 方法 2: 作为模块导入使用

```python
from generate_request_body import generate_request_body

# 设备轨迹查询示例
token = "your_user_token"
request_body = generate_request_body(
    token=token,
    uid=242487,
    sn="device_sn_12345",
    start_time=1609459200000,
    end_time=1609545600000
)

print(request_body)
# 输出: {'encryption': 'wBB7JgJ3JiX1tQC7/ZPkhGgz/BDoLn0VgAOK99uc7001VRUZ8igJfvWbe7SRB65QmyV+SCKKhCBTJpKi+5dGeKrxbHLa5IqdI3nDwwGMDGd19fFECpa3RQOU1lV9QJo0VeU+WGnPJq0='}

# 分页查询示例
request_body = generate_request_body(
    token=token,
    uid=242487,
    page_no=1,
    page_size=20
)
```

## 参数说明

### `generate_request_body()` 函数参数

- `token` (必需): 用户 token，用于加密数据
- `uid` (可选): 用户 ID
- `sn` (可选): 设备序列号，用于设备轨迹查询
- `start_time` (可选): 开始时间戳（毫秒），用于设备轨迹查询
- `end_time` (可选): 结束时间戳（毫秒），用于设备轨迹查询
- `page_no` (可选): 页码，用于分页查询
- `page_size` (可选): 每页大小，用于分页查询

## 加密算法

- 算法: 3DES (DESede)
- 模式: ECB
- 填充: PKCS5Padding (在 Python 中对应 PKCS7)
- 编码: Base64

## 示例

### 示例 1: 设备轨迹查询

```python
from generate_request_body import generate_request_body
import json

token = "your_token_here"
request_body = generate_request_body(
    token=token,
    uid=242487,
    sn="ABC123456",
    start_time=1609459200000,
    end_time=1609545600000
)

# 转换为 JSON 字符串用于 HTTP 请求
json_body = json.dumps(request_body)
print(json_body)
```

### 示例 2: 分页查询

```python
request_body = generate_request_body(
    token=token,
    uid=242487,
    page_no=1,
    page_size=20
)
```

### 示例 3: 使用 requests 库发送请求

```python
import requests
import json
from generate_request_body import generate_request_body

token = "your_token_here"
uid = 242487

# 生成请求体
request_body = generate_request_body(
    token=token,
    uid=uid,
    sn="device_sn",
    start_time=1609459200000,
    end_time=1609545600000
)

# 发送请求
url = f"https://citytag.yuminstall.top/api/interface/v2/device3/{uid}"
response = requests.post(
    url,
    json=request_body,
    headers={"Content-Type": "application/json"}
)

print(response.json())
```
