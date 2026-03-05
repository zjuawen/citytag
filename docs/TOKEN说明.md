# Token 生成和获取说明

## Token 的来源

**Token 是由服务器生成的，不是客户端生成的。**

## Token 获取流程

### 1. 用户登录

用户通过 `/api/interface/login` 接口进行登录：

**请求：**
- URL: `https://citytag.yuminstall.top/api/interface/login`
- 方法: `POST`
- 参数（QueryMap）:
  ```json
  {
    "username": "用户名",
    "password": "密码"
  }
  ```

**响应：**
```json
{
  "code": "00000",
  "msg": "成功",
  "data": {
    "id": 242487,
    "username": "用户名",
    "token": "服务器生成的token字符串",
    "nick": "昵称",
    "avatar": "头像URL",
    "usertype": 1,
    "parentid": 0,
    "createtime": "2023-01-01 00:00:00",
    "updatetime": "2023-01-01 00:00:00",
    "del": false
  }
}
```

### 2. Token 保存

登录成功后，客户端会：
1. 保存 token 到本地配置：`ConfigInfo.saveString(Constant.ConfigName.USER_TOKEN, loginRest.getData().getToken())`
2. 保存完整的用户信息到本地：`ConfigInfo.saveString(Constant.ConfigName.USER_INFO, JSON.toJSONString(loginRest.getData()))`

### 3. Token 使用

后续的 API 请求中，token 被用作：
- **加密密钥**：用于 3DES 加密请求体中的业务数据
- **身份标识**：标识当前登录的用户

## 代码位置

### 登录接口定义
- 文件: `com/hotddos/citytag/webapi/ApiService.java`
- 接口: `@POST("/api/interface/login") Observable<LoginRest> getLogin(@QueryMap Map<String, String> map)`

### 登录实现
- 文件: `com/hotddos/citytag/activity/LoginActivity.java`
- 方法: `doLogin()` (第 151-204 行)

### Token 模型
- 文件: `com/hotddos/citytag/model/LoginRest.java`
- 字段: `private String token;`

### Token 获取工具
- 文件: `com/hotddos/citytag/utils/UserUtil.java`
- 方法: `getUserInfo()` - 从本地配置读取用户信息和 token

## 重要说明

1. **Token 由服务器生成**：客户端无法自行生成 token，必须通过登录接口获取
2. **Token 用于加密**：token 作为 3DES 加密的密钥，用于加密 API 请求体
3. **Token 需要保存**：登录成功后需要将 token 保存到本地，以便后续使用
4. **Token 有效期**：token 可能有有效期限制，过期后需要重新登录

## Python 脚本中使用 Token

在使用 `generate_request_body.py` 脚本时，你需要：

1. **先通过登录接口获取 token**：
   ```python
   import requests
   
   # 登录获取 token
   login_url = "https://citytag.yuminstall.top/api/interface/login"
   login_data = {
       "username": "your_username",
       "password": "your_password"
   }
   
   response = requests.post(login_url, params=login_data)
   login_result = response.json()
   
   if login_result.get("code") == "00000":
       token = login_result["data"]["token"]
       uid = login_result["data"]["id"]
   ```

2. **使用 token 生成请求体**：
   ```python
   from generate_request_body import generate_request_body
   
   request_body = generate_request_body(
       token=token,
       uid=uid,
       sn="device_sn",
       start_time=1609459200000,
       end_time=1609545600000
   )
   ```
