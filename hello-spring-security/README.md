# hello-spring-security

后端笔试题实现：Spring Boot 3.2.0 + Spring Security 6.2（JWT 认证）。

- `POST /api/login`：用户名密码登录接口（测试账号 `test` / `123456`），成功返回 JWT
- `GET /api/hello`：需要认证的 HelloWorld 接口，携带有效 token 返回字符串 `Hello World`，否则 401

## 技术要点

- Spring Boot **3.2.0**（Spring Security 6.2，lambda DSL 配置）
- 无状态认证：禁用 CSRF / Session（`SessionCreationPolicy.STATELESS`），登录后颁发 **JWT**（jjwt 0.12，HS256 签名）
- 自定义 `JwtAuthFilter` 解析 `Authorization: Bearer <token>`，未认证请求由 `RestAuthenticationEntryPoint` 返回 JSON 401
- 登录走 `AuthenticationManager` + 内存用户（`InMemoryUserDetailsManager`），密码校验委托 Spring Security 的 `PasswordEncoder`
- 集成测试（MockMvc）：覆盖「未认证 401 / 密码错误 401 / 登录后访问成功」三条链路

## 环境要求

- JDK 17+
- Maven 3.8+（或直接用 IDEA 打开运行）

## 运行

```bash
mvn spring-boot:run
```

## 接口测试

1. 登录获取 token：

```bash
curl -X POST http://localhost:8080/api/login \
  -H "Content-Type: application/json" \
  -d '{"username":"test","password":"123456"}'
```

响应示例：

```json
{
  "token": "eyJhbGciOiJIUzI1NiJ9....",
  "tokenType": "Bearer",
  "username": "test"
}
```

2. 携带 token 访问受保护接口：

```bash
curl http://localhost:8080/api/hello \
  -H "Authorization: Bearer <上一步返回的token>"
```

返回：`Hello World`

3. 不带 token / token 错误：返回 `401` 与 `{"code":401,"message":"Unauthorized: please login first"}`；
   密码错误：返回 `401` 与 `{"code":401,"message":"Invalid username or password"}`。

## 运行测试

```bash
mvn test
```


```
