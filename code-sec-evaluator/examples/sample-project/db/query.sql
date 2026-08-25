-- 示例项目 SQL 脚本（故意埋点，仅供安全评估演示）
-- 说明：应用层通过字符串拼接生成 SQL，存在 SQL 注入风险：
--   query = "SELECT * FROM users WHERE username = '" + username + "'"

-- 建表
CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username VARCHAR(64) NOT NULL,
    password VARCHAR(64) NOT NULL
);

-- 拼接式查询示例：当 username 传入 "' OR '1'='1" 时返回全部用户
SELECT * FROM users WHERE username = '' OR '1'='1';
